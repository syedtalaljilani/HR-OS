"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet";
import "leaflet/dist/leaflet.css";
import { addressSearchAttempts } from "@/app/hr/_lib/address";

type Props = {
  value: string;
  onChange: (value: string) => void;
};

const DEFAULT_CENTER: [number, number] = [33.6844, 73.0479];
const REVERSE_URL = "https://nominatim.openstreetmap.org/reverse";
const SEARCH_URL = "https://nominatim.openstreetmap.org/search";

export default function LocationPicker({ value, onChange }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markerRef = useRef<LeafletMarker | null>(null);
  const lastPlacedRef = useRef<string>("");
  const [mapReady, setMapReady] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchFailed, setSearchFailed] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;

    void (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !containerRef.current) return;

      const map = L.map(containerRef.current).setView(DEFAULT_CENTER, 12);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);

      const icon = L.divIcon({
        className: "",
        html:
          '<div class="h-6 w-6 -translate-x-1/2 -translate-y-full rounded-full border-2 border-white bg-navy-600 shadow-lg"></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
      });
      const marker = L.marker(DEFAULT_CENTER, { icon }).addTo(map);
      markerRef.current = marker;
      mapRef.current = map;
      setMapReady(true);

      map.on("click", async (event) => {
        const { lat, lng } = event.latlng;
        marker.setLatLng([lat, lng]);
        setGeocoding(true);
        try {
          const url = `${REVERSE_URL}?format=jsonv2&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`;
          const response = await fetch(url, { headers: { Accept: "application/json" } });
          const data = (await response.json()) as { display_name?: string };
          const resolved = data?.display_name ?? `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
          lastPlacedRef.current = resolved;
          onChange(resolved);
        } catch {
          const fallback = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
          lastPlacedRef.current = fallback;
          onChange(fallback);
        } finally {
          setGeocoding(false);
        }
      });
    })();

    return () => {
      cancelled = true;
      (mapRef.current as LeafletMap | null)?.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [onChange]);

  useEffect(() => {
    if (!mapReady) return;
    const attempts = addressSearchAttempts(value);
    if (attempts.length === 0 || attempts[0] === lastPlacedRef.current) return;
    const target = attempts[0];

    const timer = window.setTimeout(async () => {
      const map = mapRef.current;
      const marker = markerRef.current;
      if (!map || !marker) return;
      if (target === lastPlacedRef.current) return;

      setSearching(true);
      setSearchFailed(false);
      let found = false;
      for (const attempt of attempts) {
        try {
          const url = `${SEARCH_URL}?format=jsonv2&limit=1&q=${encodeURIComponent(attempt)}`;
          const response = await fetch(url, { headers: { Accept: "application/json" } });
          const results = (await response.json()) as
            | Array<{ lat: string; lon: string }>
            | { error?: string };
          if (Array.isArray(results) && results.length > 0) {
            const lat = parseFloat(results[0].lat);
            const lon = parseFloat(results[0].lon);
            if (Number.isFinite(lat) && Number.isFinite(lon)) {
              marker.setLatLng([lat, lon]);
              map.flyTo([lat, lon], 15, { duration: 0.8 });
              found = true;
              break;
            }
          }
        } catch {
          /* offline or rate-limited — try the next, shorter query */
        }
      }
      if (!found) setSearchFailed(true);
      setSearching(false);
      lastPlacedRef.current = target;
    }, 500);

    return () => window.clearTimeout(timer);
  }, [value, mapReady]);

  return (
    <div>
      <div
        ref={containerRef}
        className="h-56 w-full border border-zinc-200"
        aria-label="Company location map picker"
      />
      <p className="mt-2 text-xs text-zinc-500">
        {searching
          ? "Looking up the address on the map…"
          : searchFailed
            ? "Couldn't find this address on the map — click the map to set the pin instead."
            : geocoding
              ? "Reading the address from the map…"
              : "Click anywhere on the map to set your office location — the address is filled in automatically. Typing or pasting an address updates the map too."}
      </p>
    </div>
  );
}