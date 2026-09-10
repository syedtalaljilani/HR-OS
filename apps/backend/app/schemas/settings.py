from pydantic import BaseModel


class OrgSettingsOut(BaseModel):
    company_name: str = ""
    hr_name: str = ""
    company_location: str = ""


class OrgSettingsUpdate(BaseModel):
    company_name: str = ""
    hr_name: str = ""
    company_location: str = ""