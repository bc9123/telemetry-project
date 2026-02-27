from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.org import Org
from app.db.models.project import Project
from app.db.models.device import Device
from app.db.models.api_key import ApiKey
from app.core.security import generate_api_key

def main():
    db = SessionLocal()

    org = Org(name="Demo Org")
    db.add(org); db.commit(); db.refresh(org)

    project = Project(org_id=org.id, name="Demo Project")
    db.add(project); db.commit(); db.refresh(project)

    device = Device(project_id=project.id, external_id="sensor-001", name="Sensor 001")
    db.add(device); db.commit(); db.refresh(device)

    raw, prefix, hashed = generate_api_key()
    key = ApiKey(project_id=project.id, prefix=prefix, hashed_secret=hashed)
    db.add(key); db.commit()

    print("API KEY (save this, shown once):", raw)
    print("Device external_id:", device.external_id)

    db.close()

if __name__ == "__main__":
    main()
