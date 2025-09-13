import csv, random, uuid, datetime as dt
from faker import Faker

fake = Faker("en_US")
CAUSES = ["education","food-security","environment","elder-care","animal-welfare","health"]
SKILLS = ["mentoring","event-staff","data-entry","web-dev","graphic-design","fundraising"]
ACCESS = ["wheelchair","asl","quiet-space","step-free","closed-caption"]
TAGS = ["weekend","weekday-evening","family-friendly","skills-based","remote-ok"]

def pick(pool, lo=1, hi=3): return list(set(random.sample(pool, random.randint(lo, hi))))

def new_event_row(org_id):
    eid = str(uuid.uuid4())
    mode = random.choice(["in_person","virtual","hybrid"])
    city = fake.city() if mode != "virtual" else ""
    state = fake.state_abbr() if city else ""
    is_remote = "t" if mode != "in_person" else "f"
    title = f"{random.choice(['Community','STEM','Park','Shelter','Clinic'])} {random.choice(['Cleanup','Mentoring','Drive','Support','Workshop'])}"
    desc = fake.paragraph(nb_sentences=4)
    return eid, {
        "id": eid, "organization_id": org_id, "title": title, "description": desc, "mode": mode,
        "location_city": city, "location_state": state,
        "location_lat": round(random.uniform(25, 48), 6) if city else "",
        "location_lng": round(random.uniform(-124, -67), 6) if city else "",
        "is_remote": is_remote,
        "causes": "{" + ",".join(pick(CAUSES,1,2)) + "}",
        "skills_needed": "{" + ",".join(pick(SKILLS,1,3)) + "}",
        "accessibility": "{" + ",".join(pick(ACCESS,0,2)) + "}",
        "tags": "{" + ",".join(pick(TAGS,1,3)) + "}",
        "min_duration_min": random.choice([60, 90, 120, 180]),
        "rsvp_url": fake.url(), "contact_email": fake.email()
    }

def session_rows(event_id):
    rows = []
    base = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=random.randint(2, 28))
    for i in range(random.randint(1, 3)):
        start = base + dt.timedelta(days=7*i, hours=random.choice([9, 13, 17]))
        dur = random.choice([60, 90, 120])
        end = start + dt.timedelta(minutes=dur)
        rows.append({
            "id": str(uuid.uuid4()), "event_id": event_id,
            "start_ts": start.isoformat(), "end_ts": end.isoformat(),
            "capacity": random.choice([10,20,50,100]),
            "meet_url": "" if random.random() < 0.6 else fake.url(),
            "address_line": fake.street_address()
        })
    return rows

with open("organizations.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id","name","website"])
    w.writeheader()
    for i in range(1,6):
        w.writerow({"id": i, "name": Faker().company(), "website": Faker().url()})

with open("events.csv","w",newline="") as f1, open("sessions.csv","w",newline="") as f2:
    efields = ["id","organization_id","title","description","mode","location_city","location_state",
               "location_lat","location_lng","is_remote","causes","skills_needed","accessibility",
               "tags","min_duration_min","rsvp_url","contact_email"]
    sfields = ["id","event_id","start_ts","end_ts","capacity","meet_url","address_line"]
    ew, sw = csv.DictWriter(f1, fieldnames=efields), csv.DictWriter(f2, fieldnames=sfields)
    ew.writeheader(); sw.writeheader()
    for _ in range(50):
        org_id = random.randint(1,5)
        eid, erow = new_event_row(org_id); ew.writerow(erow)
        for s in session_rows(eid): sw.writerow(s)
print("Wrote organizations.csv, events.csv, sessions.csv")