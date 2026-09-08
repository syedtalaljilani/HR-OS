import TrackForm from "@/app/_components/TrackForm";

export default function TrackPage() {
  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center px-6 py-16 text-center">
      <h1 className="text-3xl font-bold text-zinc-900">
        Track your application
      </h1>
      <p className="mt-2 text-zinc-600">
        Enter the tracking token you received after applying to see the latest
        status of your application.
      </p>
      <div className="mt-8 w-full">
        <TrackForm />
      </div>
    </main>
  );
}