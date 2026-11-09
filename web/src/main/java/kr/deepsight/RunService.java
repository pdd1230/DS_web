package kr.deepsight;
import org.springframework.stereotype.Service;import org.springframework.transaction.annotation.Transactional;
import kr.deepsight.Models.*;import java.nio.file.*;import java.util.*;
@Service
public class RunService {
 final Runs runs;final Datasets datasets;final Jobs jobs;final Results results;final Reviews reviews;final Reports reports;final FilesService f;
 public RunService(Runs r,Datasets d,Jobs j,Results re,Reviews rv,Reports rp,FilesService f){runs=r;datasets=d;jobs=j;results=re;reviews=rv;reports=rp;this.f=f;}
 @Transactional public synchronized Run create(Map<String,Object> body)throws Exception{
  String requestId=body.getOrDefault("requestId",FilesService.id()).toString();if(!requestId.matches("[0-9a-f-]{36}"))throw new IllegalArgumentException("요청 ID 오류");
  var existing=runs.findById(requestId);if(existing.isPresent())return existing.get();
  String datasetId=body.getOrDefault("datasetId","").toString();datasets.findById(datasetId).orElseThrow(()->new IllegalArgumentException("데이터셋을 선택하세요."));
  String title=body.getOrDefault("title","").toString().strip(),note=body.getOrDefault("note","").toString().strip();
  if(title.isBlank()||title.length()>200||note.isBlank()||note.length()>4000)throw new IllegalArgumentException("실험 이름(200자)과 목적(4000자)을 입력하세요.");
  String kind=body.getOrDefault("kind","compare").toString();if(!List.of("initial","baseline","compare","import_compare","import_baseline","import_initial").contains(kind))throw new IllegalArgumentException("프로그램 종류 오류");
  if(!Boolean.TRUE.equals(body.get("preserve")))throw new IllegalArgumentException("이전 결과 보존을 확인하세요.");
  Run r=new Run();r.id=requestId;r.datasetId=datasetId;r.title=title;r.note=note;r.kind=kind.replace("import_","");r.status="QUEUED";r.origin=kind.startsWith("import_")?"IMPORTED":"WEB";r.createdAt=FilesService.now();r.previousNote=body.getOrDefault("previousNote","").toString().strip();
  if(r.previousNote.isBlank()||r.previousNote.length()>4000)throw new IllegalArgumentException("보존 설명을 입력하세요.");
  Map<String,Object> settings=new LinkedHashMap<>();Object raw=body.get("settings");if(raw instanceof Map<?,?> map)map.forEach((k,v)->settings.put(k.toString(),v));
  Map<String,double[]> allowed=Map.of("YOLO_CONFIDENCE",new double[]{.01,1},"YOLO_IMAGE_SIZE",new double[]{320,1920},"MIN_FACE_SIZE",new double[]{1,500},"MOSAIC_SIZE",new double[]{2,100},"FACE_PADDING_RATIO",new double[]{0,.5});
  for(var e:settings.entrySet()){if(!allowed.containsKey(e.getKey())||!(e.getValue() instanceof Number))throw new IllegalArgumentException("설정 오류");double v=((Number)e.getValue()).doubleValue();double[] bounds=allowed.get(e.getKey());if((Set.of("YOLO_IMAGE_SIZE","MIN_FACE_SIZE","MOSAIC_SIZE").contains(e.getKey())&&v!=Math.rint(v))||!Double.isFinite(v)||v<bounds[0]||v>bounds[1])throw new IllegalArgumentException("설정 범위 오류");}
  r.settingsJson=f.encode(settings);Path base=f.safe("runs/"+r.id);Files.createDirectories(base);
  var previous=runs.findAllByOrderByCreatedAtDesc().stream().filter(x->x.currentRevision>0).findFirst();
  if(previous.isPresent()){
   Run p=previous.get();r.previousRunId=p.id;Report report=reports.findByRunIdAndRevision(p.id,p.currentRevision).orElseThrow();Path source=f.safe(report.rootPath);var entries=f.list(Files.readString(source.resolve("manifest.json")));f.verify(source,entries);
   // Previous experiment already immutable. Keep verified reference + hash list, without copying models.
   f.writeJson(base.resolve("previous_preservation.json"),Map.of("previousRunId",p.id,"reportRoot",report.rootPath,"note",r.previousNote,"verifiedAt",FilesService.now(),"files",entries));
  }
  Path data=f.safe("datasets/"+datasetId+"/data");f.verify(data,f.list(Files.readString(data.getParent().resolve("manifest.json"))));f.copyTree(data,base.resolve("data"));
  f.writeJson(base.resolve("input_manifest.json"),f.manifest(base.resolve("data")));
  runs.save(r);queue(r,kind,1);return r;
 }
 public Job queue(Run r,String kind,int revision){Job j=new Job();j.id=FilesService.id();j.runId=r.id;j.kind=kind;j.status="QUEUED";j.createdAt=FilesService.now();j.revision=revision;j.error="";return jobs.save(j);}
 @Transactional public synchronized Job reanalyze(String runId)throws Exception{
  Run r=runs.findById(runId).orElseThrow();if(!"compare".equals(r.kind)||r.currentRevision<1)throw new IllegalArgumentException("완료한 4정책 실험만 분석을 다시 실행할 수 있습니다.");
  if(jobs.findByRunIdOrderByCreatedAtDesc(runId).stream().anyMatch(j->List.of("QUEUED","RUNNING").contains(j.status)))throw new IllegalArgumentException("이미 실행 중인 작업이 있습니다.");
  int next=reports.findByRunIdOrderByRevisionDesc(runId).stream().mapToInt(p->p.revision).max().orElse(0)+1;
  // Failed attempts may already have published a file revision. Never overwrite one.
  while(Files.exists(f.safe("runs/"+runId+"/reports/r"+String.format("%04d",next))))next++;
  Job j=queue(r,"analyze",next);Path folder=f.safe("runs/"+runId+"/review_inputs/"+j.id);Files.createDirectories(folder);
  StringBuilder csv=new StringBuilder("\ufeffexperiment_id,policy,filename,review_status,review_result,missing_faces,false_faces,mosaic_quality,review_note\r\n");
  List<Map<String,Object>> snapshot=new ArrayList<>();
  for(Result result:results.findByRunIdOrderByFilenameAscPolicyAsc(runId)){
   var value=reviews.findByResultId(result.id);if(value.isEmpty())continue;Review v=value.get();
   List<String> cells=List.of(runId,result.policy,result.filename,v.done?"검수 완료":"미검수",v.done?"검수 기록 있음":"",String.valueOf(v.missingFaces),String.valueOf(v.falseFaces),v.quality,v.note);
   csv.append(cells.stream().map(RunService::csv).collect(java.util.stream.Collectors.joining(","))).append("\r\n");
   snapshot.add(Map.of("resultId",result.id,"updatedAt",v.updatedAt,"done",v.done));
  }
  Files.writeString(folder.resolve("manual_review.csv"),csv);f.writeJson(folder.resolve("snapshot.json"),snapshot);r.status="RUNNING";r.error="";runs.save(r);return j;
 }
 public static String csv(String s){return "\""+s.replace("\"","\"\"")+"\"";}
}
