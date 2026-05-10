export const API_BASE_URL = "/api";

export interface Movie {
  id:string;tmdb_id:number;title:string;title_ar:string;
  overview:string;overview_ar:string;poster_path:string;backdrop_path:string;
  release_date:string;runtime:number;genres:string[];cast:any[];
  director:string;rating:number;vote_count:number;
  file_id?:string;file_size?:number;has_file:boolean;stream_url?:string;
}
export interface Series {
  id:string;tmdb_id:number;title:string;title_ar:string;
  overview:string;overview_ar:string;poster_path:string;backdrop_path:string;
  first_air_date:string;genres:string[];cast:any[];creator:string;
  rating:number;vote_count:number;total_seasons:number;status:string;
  seasons?:Record<string,Episode[]>;total_seasons_available?:number;
  has_file?:boolean;
}
export interface Episode {
  id:number;series_id:string;season_number:number;episode_number:number;
  title:string;overview:string;still_path:string;air_date:string;
  runtime:number;file_id?:string;file_size?:number;has_file:boolean;stream_url?:string;
}
export interface FeaturedItem {
  id:string;type:"movie"|"series";title:string;title_ar:string;
  poster_path:string;backdrop_path:string;rating:number;date:string;
  overview:string;overview_ar:string;genres:string[];
}
async function get<T>(path:string,params?:Record<string,any>):Promise<T>{
  const url=new URL(path,window.location.origin);
  if(params) Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!==null&&v!=="")url.searchParams.set(k,String(v));});
  const res=await fetch(url.toString());
  if(!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
async function post<T>(path:string,body:any):Promise<T>{
  const url=new URL(path,window.location.origin);
  const res=await fetch(url.toString(),{
    method:"POST",
    headers:{"Content-Type":"application/json","X-Admin-ID":"5703679073"},
    body:JSON.stringify(body)
  });
  if(!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
async function del<T>(path:string):Promise<T>{
  const url=new URL(path,window.location.origin);
  const res=await fetch(url.toString(),{
    method:"DELETE",
    headers:{"X-Admin-ID":"5703679073"}
  });
  if(!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
async function getAdmin<T>(path:string,params?:Record<string,any>):Promise<T>{
  const url=new URL(path,window.location.origin);
  if(params) Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!==null&&v!=="")url.searchParams.set(k,String(v));});
  const res=await fetch(url.toString(),{headers:{"X-Admin-ID":"5703679073"}});
  if(!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
export const api={
  featured:()=>get<{items:FeaturedItem[]}>("/api/featured"),
  movies:(p?:{limit?:number;offset?:number;genre?:string;search?:string;sort?:string;has_file?:boolean})=>get<{items:Movie[];total:number}>("/api/movies",p),
  movie:(id:string)=>get<Movie>(`/api/movies/${id}`),
  series:(p?:{limit?:number;offset?:number;genre?:string;search?:string;sort?:string})=>get<{items:Series[];total:number}>("/api/series",p),
  seriesDetail:(id:string)=>get<Series>(`/api/series/${id}`),
  episodes:(id:string,season?:number)=>get<{items:Episode[]}>(`/api/series/${id}/episodes`,season?{season}:undefined),
  search:(q:string)=>get<{movies:Movie[];series:Series[];query:string}>("/api/search",{q}),
  genres:()=>get<{genres:string[]}>("/api/genres"),
  stats:()=>get<any>("/api/stats"),
  // Watch Rooms API
  rooms:{
    getActive:(p?:{limit?:number;offset?:number;content_type?:string;is_public?:boolean})=>get<{rooms:any[];count:number}>("/api/rooms/active",p),
    getDetails:(roomId:string)=>get<{success:boolean;room:any}>(`/api/rooms/${roomId}`),
    create:(data:any)=>post<{success:boolean;room:any}>("/api/rooms/create",data),
    join:(roomId:string,data:{user_id:number;password?:string})=>post<{success:boolean;room:any}>(`/api/rooms/${roomId}/join`,data),
    leave:(roomId:string,userId:number)=>post<{success:boolean}>(`/api/rooms/${roomId}/leave?user_id=${userId}`,{}),
    updateSettings:(roomId:string,data:any)=>post<{success:boolean;room:any}>(`/api/rooms/${roomId}/settings`,data),
    delete:(roomId:string,userId:number)=>del<{success:boolean}>(`/api/rooms/${roomId}?user_id=${userId}`),
    search:(query:string,limit?:number)=>get<{rooms:any[];count:number}>("/api/rooms/search",{query,limit}),
    // Sync
    syncPlayback:(roomId:string,data:any)=>post<{success:boolean;sync_state:any}>(`/api/rooms/${roomId}/sync`,data),
    getSyncState:(roomId:string)=>get<{success:boolean;sync_state:any}>(`/api/rooms/${roomId}/sync`),
    resync:(roomId:string,userId:number)=>post<{success:boolean;sync_state:any}>(`/api/rooms/${roomId}/resync?user_id=${userId}`,{}),
    // Chat
    sendMessage:(roomId:string,data:any)=>post<{success:boolean;message:any}>(`/api/rooms/${roomId}/chat`,data),
    getMessages:(roomId:string,p?:{limit?:number;offset?:number;before_id?:number})=>get<{messages:any[];count:number}>(`/api/rooms/${roomId}/chat`,p),
    deleteMessage:(roomId:string,messageId:number,userId:number)=>del<{success:boolean}>(`/api/rooms/${roomId}/chat/${messageId}?user_id=${userId}`),
    // Participants
    getParticipants:(roomId:string)=>get<{participants:any[];count:number}>(`/api/rooms/${roomId}/participants`),
  }
};
export const adminApi={
  getStats:()=>getAdmin<any>("/api/admin/stats"),
  getUsers:(p:{limit:number;offset:number;search?:string;blocked_only:boolean})=>getAdmin<{users:any[];total:number}>("/api/admin/users",p),
  getUser:(id:number)=>getAdmin<any>(`/api/admin/users/${id}`),
  blockUser:(id:number)=>post<any>(`/api/admin/users/${id}/block`,{}),
  unblockUser:(id:number)=>post<any>(`/api/admin/users/${id}/unblock`,{}),
  deleteUser:(id:number)=>del<any>(`/api/admin/users/${id}`),
  getContent:(p:{content_type:string;limit:number;offset:number;search?:string})=>getAdmin<{items:any[];total:number;content_type:string}>("/api/admin/content",p),
  deleteContent:(type:string,id:string)=>del<any>(`/api/admin/content/${type}/${id}`),
  triggerFullScan:()=>post<any>("/api/admin/fullscan",{}),
  getAuditLogs:(p:{limit:number;offset:number;action_type?:string;start_date?:string;end_date?:string})=>getAdmin<{logs:any[];total:number}>("/api/admin/audit-logs",p),
  getNotifications:(p:{limit:number;offset:number;status?:string})=>getAdmin<{notifications:any[];total:number}>("/api/admin/notifications",p),
  createNotification:(data:any)=>post<any>("/api/admin/notifications",data),
  getBotStatus:()=>getAdmin<any>("/api/admin/bot-status"),
  getSyncStatus:()=>getAdmin<any>("/api/admin/sync-status"),
  syncDB:()=>post<any>("/api/admin/sync-db",{}),
};
