import { useEffect, useState } from "react";
import api from "../api";

export default function Events(){
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/events")
      .then(res => setEvents(res.data))
      .catch(e => setErr(e?.message || "Failed to load"))
      .finally(()=> setLoading(false));
  }, []);

  if (loading) return <div style={{maxWidth:800, margin:"40px auto"}}>Loading…</div>;
  if (err) return <div style={{maxWidth:800, margin:"40px auto", color:"crimson"}}>{err}</div>;

  return (
    <div style={{maxWidth:800, margin:"40px auto"}}>
      <h2>Events</h2>
      <div style={{display:"grid", gap:12}}>
        {events.map(ev => (
          <div key={ev.id} style={{border:"1px solid #eee", padding:12, borderRadius:8}}>
            <b>{ev.title}</b> <span style={{opacity:.7}}>{ev.city ?? "Remote"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
