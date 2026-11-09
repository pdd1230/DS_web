CREATE TABLE dataset (
  id VARCHAR(255) PRIMARY KEY,
  name VARCHAR(255),
  parent_id VARCHAR(255),
  created_at VARCHAR(255),
  ground_truth LONGTEXT
);

CREATE TABLE dataset_image (
  id VARCHAR(255) PRIMARY KEY,
  dataset_id VARCHAR(255),
  filename VARCHAR(255),
  ground_truth INT NOT NULL,
  scene VARCHAR(255),
  note VARCHAR(2000),
  width INT NOT NULL,
  height INT NOT NULL,
  size BIGINT NOT NULL,
  sha256 VARCHAR(255),
  UNIQUE (dataset_id,filename),
  FOREIGN KEY (dataset_id) REFERENCES dataset(id)
);

CREATE TABLE experiment (
  id VARCHAR(255) PRIMARY KEY,
  dataset_id VARCHAR(255),
  title VARCHAR(255),
  kind VARCHAR(255),
  status VARCHAR(255),
  created_at VARCHAR(255),
  completed_at VARCHAR(255),
  previous_run_id VARCHAR(255),
  origin VARCHAR(255),
  note VARCHAR(4000),
  previous_note VARCHAR(4000),
  error VARCHAR(4000),
  settings_json LONGTEXT,
  current_revision INT NOT NULL,
  FOREIGN KEY (dataset_id) REFERENCES dataset(id)
);

CREATE TABLE experiment_job (
  id VARCHAR(255) PRIMARY KEY,
  run_id VARCHAR(255),
  kind VARCHAR(255),
  status VARCHAR(255),
  created_at VARCHAR(255),
  progress INT NOT NULL,
  revision INT NOT NULL,
  error VARCHAR(4000),
  FOREIGN KEY (run_id) REFERENCES experiment(id)
);

CREATE TABLE image_policy_result (
  id VARCHAR(255) PRIMARY KEY,
  run_id VARCHAR(255),
  filename VARCHAR(255),
  policy VARCHAR(255),
  evaluation VARCHAR(255),
  processing_status VARCHAR(255),
  scene VARCHAR(255),
  ground_truth INT NOT NULL,
  detected INT,
  review_required BOOLEAN NOT NULL,
  note VARCHAR(2000),
  image_path VARCHAR(1000),
  UNIQUE (run_id,filename,policy),
  FOREIGN KEY (run_id) REFERENCES experiment(id)
);

CREATE TABLE detection_candidate (
  id VARCHAR(255) PRIMARY KEY,
  result_id VARCHAR(255),
  payload LONGTEXT,
  FOREIGN KEY (result_id) REFERENCES image_policy_result(id)
);

CREATE TABLE detected_face (
  id VARCHAR(255) PRIMARY KEY,
  result_id VARCHAR(255),
  payload LONGTEXT,
  FOREIGN KEY (result_id) REFERENCES image_policy_result(id)
);

CREATE TABLE manual_review (
  id VARCHAR(255) PRIMARY KEY,
  result_id VARCHAR(255),
  done BOOLEAN NOT NULL,
  missing_faces INT NOT NULL,
  false_faces INT NOT NULL,
  quality VARCHAR(255),
  note VARCHAR(4000),
  updated_at VARCHAR(255),
  UNIQUE (result_id),
  FOREIGN KEY (result_id) REFERENCES image_policy_result(id)
);

CREATE TABLE report_revision (
  id VARCHAR(255) PRIMARY KEY,
  run_id VARCHAR(255),
  revision INT NOT NULL,
  root_path VARCHAR(255),
  created_at VARCHAR(255),
  summary_json LONGTEXT,
  review_snapshot LONGTEXT,
  UNIQUE (run_id,revision),
  FOREIGN KEY (run_id) REFERENCES experiment(id)
);

CREATE TABLE artifact (
  id VARCHAR(255) PRIMARY KEY,
  report_id VARCHAR(255),
  path VARCHAR(500),
  size BIGINT NOT NULL,
  sha256 VARCHAR(255),
  UNIQUE (report_id,path),
  FOREIGN KEY (report_id) REFERENCES report_revision(id)
);
