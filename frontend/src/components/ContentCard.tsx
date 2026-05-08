import { Star } from "lucide-react";

interface Props {
  id: string; type: "movie"|"series"; title: string; title_ar: string;
  poster_path: string; rating: number; has_file?: boolean; year?: string; onClick: ()=>void;
}

export default function ContentCard({ type, title, title_ar, poster_path, rating, has_file, year, onClick }: Props) {
  const displayTitle = title_ar || title;
  const yr = year?.slice(0, 4) || "";
  return (
    <div onClick={onClick} style={{ cursor:"pointer", flexShrink:0, width:130, transition:"transform 0.2s" }}
      onTouchStart={e=>(e.currentTarget.style.transform="scale(0.95)")}
      onTouchEnd={e=>(e.currentTarget.style.transform="scale(1)")}>
      <div style={{
        position:"relative",borderRadius:10,overflow:"hidden",aspectRatio:"2/3",
        background:"#1a1a2e",boxShadow:"0 4px 16px rgba(0,0,0,0.5)",
      }}>
        {poster_path
          ? <img src={poster_path} alt={displayTitle} style={{width:"100%",height:"100%",objectFit:"cover"}} loading="lazy"/>
          : <div style={{width:"100%",height:"100%",display:"flex",alignItems:"center",justifyContent:"center",fontSize:40}}>🎬</div>
        }
        {rating > 0 && (
          <div style={{
            position:"absolute",top:6,right:6,background:"rgba(0,0,0,0.78)",borderRadius:6,
            padding:"2px 6px",display:"flex",alignItems:"center",gap:2,backdropFilter:"blur(4px)",
          }}>
            <Star size={9} fill="#f59e0b" color="#f59e0b"/>
            <span style={{fontSize:10,color:"#f59e0b",fontWeight:700}}>{rating.toFixed(1)}</span>
          </div>
        )}
        <div style={{
          position:"absolute",top:6,left:6,
          background:type==="series"?"rgba(139,92,246,0.85)":"rgba(16,185,129,0.85)",
          borderRadius:4,padding:"1px 5px",fontSize:9,fontWeight:700,
        }}>{type==="series"?"مسلسل":"فيلم"}</div>
        {has_file === false && (
          <div style={{position:"absolute",inset:0,background:"rgba(0,0,0,0.5)",display:"flex",alignItems:"flex-end",justifyContent:"center",paddingBottom:8}}>
            <span style={{fontSize:9,color:"rgba(255,255,255,0.6)",background:"rgba(0,0,0,0.5)",padding:"2px 6px",borderRadius:4}}>قريباً</span>
          </div>
        )}
      </div>
      <div style={{marginTop:6,paddingRight:2}}>
        <p style={{fontSize:12,fontWeight:600,lineHeight:1.3,color:"#fff",overflow:"hidden",display:"-webkit-box",WebkitLineClamp:2,WebkitBoxOrient:"vertical" as any}}>{displayTitle}</p>
        {yr && <p style={{fontSize:10,color:"rgba(255,255,255,0.4)",marginTop:2}}>{yr}</p>}
      </div>
    </div>
  );
}
