import type {GitHubRepo,GitHubStatus,Health,Repo,Run,TestResult,ToolDescriptor} from '../types';
const BASE=import.meta.env.VITE_API_URL||'http://127.0.0.1:8000/api';
async function json<T>(url:string,init?:RequestInit):Promise<T>{
 const r=await fetch(BASE+url,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}});
 if(!r.ok){let message=`HTTP ${r.status}`;try{const body=await r.json();message=body.detail||body.message||message}catch{const text=await r.text();if(text)message=text}throw new Error(message)}
 return r.json();
}
export const api={
 demo:()=>json<Repo>('/repositories/demo'),
 connect:(url:string,branch='main')=>json<Repo>('/repositories/connect',{method:'POST',body:JSON.stringify({url,branch})}),
 githubStatus:()=>json<GitHubStatus>('/repositories/github/status'),
 githubRepos:()=>json<GitHubRepo[]>('/repositories/github'),
 connectGitHub:(full_name:string,branch?:string)=>json<Repo>('/repositories/github/connect',{method:'POST',body:JSON.stringify({full_name,branch:branch||null})}),
 ask:(repository_id:string,question:string)=>json<Run>('/agent/runs',{method:'POST',body:JSON.stringify({repository_id,question})}),
 run:(id:string)=>json<Run>(`/agent/runs/${id}`),
 tests:(id:string,command='pytest')=>json<TestResult>(`/agent/runs/${id}/tests`,{method:'POST',body:JSON.stringify({command,apply_patch:true})}),
 health:()=>json<Health>('/health'),
 tools:()=>json<{tools:ToolDescriptor[]}>('/tools'),
 eventsUrl:(id:string)=>`${BASE}/agent/runs/${id}/events`
};
