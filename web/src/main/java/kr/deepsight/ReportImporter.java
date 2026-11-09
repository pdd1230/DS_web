package kr.deepsight;
import org.springframework.stereotype.Service;import org.springframework.transaction.annotation.Transactional;
import kr.deepsight.Models.*;import java.nio.file.*;import java.nio.charset.StandardCharsets;import java.util.*;
@Service
public class ReportImporter {
 final Images images;final Runs runs;final Jobs jobs;final Results results;final Candidates candidates;final Faces faces;final Reports reports;final Artifacts artifacts;final FilesService f;
 public ReportImporter(Images im,Runs r,Jobs j,Results re,Candidates c,Faces fa,Reports rp,Artifacts a,FilesService f){images=im;runs=r;jobs=j;results=re;candidates=c;faces=fa;reports=rp;artifacts=a;this.f=f;}
 static String stable(String s){return UUID.nameUUIDFromBytes(s.getBytes(StandardCharsets.UTF_8)).toString();}
 @Transactional public void accept(String jobId,String rootPath)throws Exception{
  Job j=jobs.findById(jobId).orElseThrow();Run r=runs.findById(j.runId).orElseThrow();
  String expected="runs/"+r.id+"/reports/r"+String.format("%04d",j.revision);
  if(!rootPath.equals(expected))throw new IllegalArgumentException("결과 경로 불일치");Path dir=f.safe(rootPath);
  List<Map<String,Object>> manifest=f.list(Files.readString(dir.resolve("manifest.json")));f.verify(dir,manifest);
  Map<String,Object> bundle=f.object(Files.readString(dir.resolve("bundle.json")));
  if(!r.id.equals(bundle.get("experimentId"))||((Number)bundle.get("revision")).intValue()!=j.revision)throw new IllegalArgumentException("실험/개정 ID 불일치");
  List<?> rows=(List<?>)bundle.get("results");if(rows==null||rows.isEmpty())throw new IllegalArgumentException("결과 행 없음");
  Set<String> keys=new HashSet<>();Map<String,DsImage> inputs=new HashMap<>();for(DsImage im:images.findByDatasetIdOrderByFilename(r.datasetId))inputs.put(im.filename,im);Set<String> allowed=r.kind.equals("compare")?Set.of("legacy","yolo_only","haar_only","improved"):Set.of(r.kind);if(rows.size()!=inputs.size()*allowed.size())throw new IllegalArgumentException("사진/정책 결과 행 수 불일치");
  for(Object object:rows){
   Map<?,?> row=(Map<?,?>)object;String fn=row.get("filename").toString(),policy=row.get("policy").toString();FilesService.filename(fn);if(!inputs.containsKey(fn)||!allowed.contains(policy)||inputs.get(fn).groundTruth!=((Number)row.get("groundTruth")).intValue())throw new IllegalArgumentException("입력 사진/정책/정답 불일치");
   if(!keys.add(fn+"/"+policy))throw new IllegalArgumentException("중복 결과");
   Result result=results.findByRunIdAndFilenameAndPolicy(r.id,fn,policy).orElseGet(Result::new);if(result.id==null)result.id=stable(r.id+"/"+fn+"/"+policy);
   result.runId=r.id;result.filename=fn;result.policy=policy;result.groundTruth=((Number)row.get("groundTruth")).intValue();result.detected=row.get("detected")==null?null:((Number)row.get("detected")).intValue();result.evaluation=row.get("evaluation").toString();result.processingStatus=row.get("processingStatus").toString();result.reviewRequired=Boolean.TRUE.equals(row.get("reviewRequired"));result.scene=String.valueOf(row.get("scene"));result.note=String.valueOf(row.get("note"));
   String image=String.valueOf(row.get("image"));if(!dir.resolve("outputs").resolve(image).normalize().startsWith(dir.resolve("outputs")))throw new IllegalArgumentException("결과 경로 이탈");result.imagePath=image.isBlank()?"":rootPath+"/outputs/"+image;
   if(!result.imagePath.isBlank()&&!Files.isRegularFile(f.safe(result.imagePath)))throw new IllegalArgumentException("결과 이미지 없음");results.save(result);
   int index=0;for(Object c:(List<?>)row.get("candidates")){Candidate candidate=new Candidate();candidate.id=stable(result.id+"/candidate/"+index++);candidate.resultId=result.id;candidate.payload=f.encode(c);candidates.save(candidate);}
   index=0;for(Object face:(List<?>)row.get("faces")){Face fa=new Face();fa.id=stable(result.id+"/face/"+index++);fa.resultId=result.id;fa.payload=f.encode(face);faces.save(fa);}
  }
  Report report=reports.findByRunIdAndRevision(r.id,j.revision).orElseGet(Report::new);if(report.id==null)report.id=FilesService.id();report.runId=r.id;report.revision=j.revision;report.rootPath=rootPath;report.createdAt=FilesService.now();report.summaryJson=f.encode(bundle.get("summaries"));
  Path snapshot=f.safe("runs/"+r.id+"/review_inputs/"+j.id+"/snapshot.json");report.reviewSnapshot=Files.exists(snapshot)?Files.readString(snapshot):"[]";reports.save(report);
  for(var row:manifest){Artifact a=new Artifact();a.id=stable(report.id+"/"+row.get("path"));a.reportId=report.id;a.path=row.get("path").toString();a.size=((Number)row.get("size")).longValue();a.sha256=row.get("sha256").toString();artifacts.save(a);}
  r.currentRevision=j.revision;r.status="COMPLETED";r.error="";r.completedAt=FilesService.now();runs.save(r);j.status="COMPLETED";j.progress=100;j.error="";jobs.save(j);
 }
}
