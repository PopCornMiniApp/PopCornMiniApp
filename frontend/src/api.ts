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
};
