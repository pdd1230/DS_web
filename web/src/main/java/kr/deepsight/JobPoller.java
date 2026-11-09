package kr.deepsight;
import org.springframework.stereotype.Component;import org.springframework.scheduling.annotation.Scheduled;
import kr.deepsight.Models.*;import java.util.*;
@Component
public class JobPoller {
 final Jobs jobs;final Runs runs;final FilesService f;final PythonClient python;final ReportImporter importer;
 public JobPoller(Jobs j,Runs r,FilesService f,PythonClient p,ReportImporter i){jobs=j;runs=r;this.f=f;python=p;importer=i;}
 @Scheduled(fixedDelay=2000) public synchronized void tick(){
  for(Job j:jobs.findByStatusIn(List.of("QUEUED","RUNNING"))){
   Run r=runs.findById(j.runId).orElseThrow();
   try{
    Map<String,Object> answer;
    if(j.status.equals("QUEUED")){
     answer=python.request("/jobs",Map.of("jobId",j.id,"runId",r.id,"kind",j.kind,"revision",j.revision,"settings",f.object(r.settingsJson)));
     j.status="RUNNING";r.status="RUNNING";runs.save(r);jobs.save(j);
    }
    answer=python.request("/jobs/"+j.id,null);j.progress=((Number)answer.getOrDefault("progress",0)).intValue();j.error="";
    String status=answer.get("status").toString();
    if(status.equals("COMPLETED")){
     r.status="IMPORTING";runs.save(r);
     try{importer.accept(j.id,answer.get("report").toString());}catch(Exception e){j.status="IMPORT_FAILED";j.error=shortError(e);jobs.save(j);r.status="IMPORT_FAILED";r.error=j.error;runs.save(r);}
    }else if(status.equals("FAILED")){j.status="FAILED";j.error=String.valueOf(answer.get("error"));jobs.save(j);r.status="FAILED";r.error=j.error;runs.save(r);}
    else jobs.save(j);
   }catch(Exception e){
    j.error=shortError(e);
    // Temporary connection failures remain recoverable across Spring/Python restarts.
    if(e instanceof IllegalArgumentException||java.time.Duration.between(java.time.OffsetDateTime.parse(j.createdAt),java.time.OffsetDateTime.now()).toHours()>=2){j.status="FAILED";r.status="FAILED";r.error=(e instanceof IllegalArgumentException?"요청 검증 실패: ":"연결/처리 제한 시간 초과: ")+j.error;runs.save(r);}
    jobs.save(j);
   }
  }
 }
 static String shortError(Exception e){String s=e.getMessage()==null?e.toString():e.getMessage();return s.substring(0,Math.min(3900,s.length()));}
}
