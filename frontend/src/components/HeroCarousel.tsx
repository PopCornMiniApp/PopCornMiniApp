import { useState, useEffect, useCallback, useRef } from "react";
import { Play, Star, ChevronLeft, ChevronRight } from "lucide-react";
import type { FeaturedItem } from "../api";

interface Props { items: FeaturedItem[]; navigate: (r: any) => void; }

export default function HeroCarousel({ items, navigate }: Props) {
  const [current, setCurrent] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval>|null>(null);

  const goTo = useCallback((idx: number) => {
    if (transitioning) return;
    setTransitioning(true);
    setCurrent(idx);
    setTimeout(() => setTransitioning(false), 600);
  }, [transitioning]);

  const next = useCallback(() => goTo((current + 1) % items.length), [current, items.length, goTo]);
  const prev = useCallback(() => goTo((current - 1 + items.length) % items.length), [current, items.length, goTo]);

  const resetTimer = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(next, 5500);
  };

  useEffect(() => { timer.current = setInterval(next, 5500); return () => { if(timer.current) clearInterval(timer.current); }; }, [next]);

  if (!items.length) return null;
  const item = items[current];

  return (
    <div style={{ position:"relative", height:"70vw", maxHeight:360, overflow:"hidden" }}>
      {items.map((it, i) => (
        <div key={it.id} style={{
          position:"absolute",inset:0,opacity:i===current?1:0,
          transition:"opacity 0.7s ease",zIndex:i===current?1:0,
        }}>
          <img src={it.backdrop_path||it.poster_path} alt="" style={{width:"100%",height:"100%",objectFit:"cover",objectPosition:"center top"}}/>
          <div style={{position:"absolute",inset:0,background:"linear-gradient(to bottom,rgba(13,13,13,0.05) 0%,rgba(13,13,13,0.5) 55%,rgba(13,13,13,0.98) 100%)"}}/>
        </div>
      ))}

      <div style={{
        position:"absolute",bottom:0,left:0,right:0,zIndex:10,padding:"0 16px 18px",
        opacity:transitioning?0:1,transform:transitioning?"translateY(10px)":"translateY(0)",
        transition:"opacity 0.4s,transform 0.4s",
      }}>
        {item.genres?.length > 0 && (
          <div style={{display:"flex",gap:6,marginBottom:8,flexWrap:"wrap"}}>
            {item.genres.slice(0,3).map((g:string)=>(
              <span key={g} style={{fontSize:10,padding:"2px 8px",borderRadius:20,background:"rgba(139,92,246,0.35)",border:"1px solid rgba(139,92,246,0.5)",color:"#c4b5fd"}}>{g}</span>
            ))}
          </div>
        )}
        <h2 style={{fontSize:21,fontWeight:800,lineHeight:1.2,marginBottom:5,textShadow:"0 2px 10px rgba(0,0,0,0.9)"}}>{item.title_ar||item.title}</h2>
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:12}}>
          {item.rating>0 && <span style={{display:"flex",alignItems:"center",gap:3,color:"#f59e0b",fontSize:12,fontWeight:700}}><Star size={11} fill="#f59e0b"/>{item.rating.toFixed(1)}</span>}
          {item.date && <span style={{fontSize:11,color:"rgba(255,255,255,0.5)"}}>{item.date.slice(0,4)}</span>}
          <span style={{fontSize:10,padding:"2px 6px",borderRadius:4,background:item.type==="series"?"rgba(139,92,246,0.7)":"rgba(16,185,129,0.7)"}}>{item.type==="series"?"مسلسل":"فيلم"}</span>
        </div>
        <button
          onClick={() => item.type==="movie" ? navigate({page:"movie",id:item.id}) : navigate({page:"series",id:item.id})}
          style={{display:"flex",alignItems:"center",gap:6,background:"#8b5cf6",color:"#fff",padding:"10px 22px",borderRadius:24,fontWeight:700,fontSize:13,boxShadow:"0 4px 20px rgba(139,92,246,0.5)"}}
        ><Play size={15} fill="#fff"/> مشاهدة الآن</button>
      </div>

      <button onClick={()=>{prev();resetTimer();}} style={{position:"absolute",right:10,top:"38%",zIndex:20,background:"rgba(0,0,0,0.45)",borderRadius:"50%",padding:7,backdropFilter:"blur(4px)"}}><ChevronRight size={16}/></button>
      <button onClick={()=>{next();resetTimer();}} style={{position:"absolute",left:10,top:"38%",zIndex:20,background:"rgba(0,0,0,0.45)",borderRadius:"50%",padding:7,backdropFilter:"blur(4px)"}}><ChevronLeft size={16}/></button>

      <div style={{position:"absolute",top:14,left:0,right:0,zIndex:10,display:"flex",justifyContent:"center",gap:5}}>
        {items.map((_,i)=>(
          <button key={i} onClick={()=>{goTo(i);resetTimer();}} style={{
            width:i===current?20:6,height:6,borderRadius:3,padding:0,
            background:i===current?"#8b5cf6":"rgba(255,255,255,0.28)",transition:"width 0.35s,background 0.35s",
          }}/>
        ))}
      </div>
    </div>
  );
}
