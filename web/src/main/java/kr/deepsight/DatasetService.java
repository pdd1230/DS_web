package kr.deepsight;
import org.springframework.stereotype.Service;import org.springframework.transaction.annotation.Transactional;import org.springframework.web.multipart.MultipartFile;
import kr.deepsight.Models.*;
import java.nio.file.*;import java.util.*;
@Service
public class DatasetService {
 final Datasets datasets;final Images images;final FilesService f;final PythonClient python;
 public DatasetService(Datasets d,Images i,FilesService f,PythonClient p){datasets=d;images=i;this.f=f;python=p;}
 @Transactional public synchronized Dataset create(String name,String gt,List<MultipartFile> photos,String parent,boolean sample)throws Exception{
  if(name==null||name.isBlank()||name.length()>200)throw new IllegalArgumentException("데이터셋 이름은 1~200자입니다.");
  String id=FilesService.id();Path data=f.safe("datasets/"+id+"/data");Files.createDirectories(data.resolve("images"));
  if(sample){f.copyTree(f.home.resolve("legacy/data/images"),data.resolve("images"));gt=Files.readString(f.home.resolve("legacy/data/ground_truth.csv"));}
  else if(parent!=null&&!parent.isBlank()){
   datasets.findById(parent).orElseThrow();f.copyTree(f.safe("datasets/"+parent+"/data/images"),data.resolve("images"));
  }else{
   if(photos==null||photos.isEmpty()||photos.size()>200)throw new IllegalArgumentException("사진 1~200장을 선택하세요.");
   Set<String> names=new HashSet<>();
   for(MultipartFile photo:photos){String n=FilesService.filename(photo.getOriginalFilename());if(photo.getSize()>25L*1024*1024||photo.isEmpty())throw new IllegalArgumentException("사진 크기는 1바이트~25MB입니다.");if(!names.add(n.toLowerCase(Locale.ROOT)))throw new IllegalArgumentException("파일명 중복: "+n);try(var in=photo.getInputStream()){Files.copy(in,data.resolve("images").resolve(n));}}
  }
  if(gt==null||gt.isBlank()||gt.length()>1_000_000)throw new IllegalArgumentException("정답표가 비어 있거나 너무 큽니다.");
  Files.writeString(data.resolve("ground_truth.csv"),gt);
  var validated=python.request("/datasets/validate",Map.of("datasetId",id));
  Dataset d=new Dataset();d.id=id;d.name=name;d.parentId=parent;d.groundTruth=gt;d.createdAt=FilesService.now();datasets.save(d);
  for(Object obj:(List<?>)validated.get("images")){
   var row=(Map<?,?>)obj;DsImage im=new DsImage();im.id=FilesService.id();im.datasetId=id;im.filename=row.get("filename").toString();im.groundTruth=((Number)row.get("groundTruth")).intValue();im.width=((Number)row.get("width")).intValue();im.height=((Number)row.get("height")).intValue();im.size=((Number)row.get("size")).longValue();im.sha256=row.get("sha256").toString();im.scene=row.get("scene").toString();im.note=row.get("note").toString();images.save(im);
  }
  f.writeJson(data.getParent().resolve("manifest.json"),f.manifest(data));
  return d;
 }
}
