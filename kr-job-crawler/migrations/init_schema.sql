-- DDL for job_postings table
-- 스키마 정의: 식별/출처, 원문, 표준화, IT분류/스킬, 프로비넌스, 관리

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS job_postings (
    -- A. 식별/출처
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    canonical_job_id VARCHAR(500) NOT NULL,
    source_platform VARCHAR(100),
    
    -- B. 원문
    company_name_raw VARCHAR(500),
    job_title_raw VARCHAR(1000),
    department_raw VARCHAR(500),
    team_raw VARCHAR(500),
    category_raw VARCHAR(500),
    employment_type_raw VARCHAR(200),
    location_raw VARCHAR(1000),
    post_date_raw VARCHAR(200),
    close_date_raw VARCHAR(200),
    detail_html TEXT,
    detail_json JSONB,
    
    -- C. 표준화
    title VARCHAR(1000),
    employment_type VARCHAR(100),
    location_country VARCHAR(100),
    location_city VARCHAR(200),
    post_date DATE,
    close_date DATE,
    is_active BOOLEAN DEFAULT true,
    
    -- D. IT 분류/스킬
    site_category_path VARCHAR(1000),
    skills TEXT[],
    it_label BOOLEAN,
    label_source VARCHAR(50), -- site|rule|model|mixed
    label_confidence NUMERIC(5, 4),
    label_evidence JSONB,
    
    -- E. 프로비넌스
    pattern_detected VARCHAR(100),
    route VARCHAR(500),
    api_endpoint TEXT,
    api_operation VARCHAR(200),
    api_params JSONB,
    selectors_used JSONB,
    site_filter_selector VARCHAR(500),
    site_filter_route VARCHAR(500),
    site_filter_api_params JSONB,
    profile_version VARCHAR(50),
    snapshot_hash VARCHAR(64),
    
    -- F. 관리
    country_filter VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 중복 방지 제약
    CONSTRAINT unique_domain_job UNIQUE (domain, canonical_job_id)
);

-- 인덱스 생성
CREATE INDEX idx_job_postings_domain ON job_postings(domain);
CREATE INDEX idx_job_postings_it_label ON job_postings(it_label);
CREATE INDEX idx_job_postings_post_date ON job_postings(post_date);
CREATE INDEX idx_job_postings_is_active ON job_postings(is_active);
CREATE INDEX idx_job_postings_source_url_hash ON job_postings USING hash(source_url);
CREATE INDEX idx_job_postings_api_endpoint ON job_postings(api_endpoint);

-- GIN 인덱스 (JSON/배열 검색용)
CREATE INDEX idx_job_postings_skills_gin ON job_postings USING gin(skills);
CREATE INDEX idx_job_postings_label_evidence_gin ON job_postings USING gin(label_evidence);
CREATE INDEX idx_job_postings_detail_json_gin ON job_postings USING gin(detail_json);

-- Updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_job_postings_updated_at 
    BEFORE UPDATE ON job_postings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 코멘트
COMMENT ON TABLE job_postings IS '통합 채용공고 데이터 - 원문/표준화/프로비넌스 포함';
COMMENT ON COLUMN job_postings.canonical_job_id IS '사이트별 고유 공고 ID (중복 방지용)';
COMMENT ON COLUMN job_postings.it_label IS 'IT 직군 여부 (분류 결과)';
COMMENT ON COLUMN job_postings.label_source IS '분류 출처: site(사이트 직접), rule(룰), model(모델), mixed';
COMMENT ON COLUMN job_postings.pattern_detected IS '탐지된 크롤링 패턴 (static_toggle|a_link|function|hash_routing|api_direct)';
COMMENT ON COLUMN job_postings.snapshot_hash IS '공고 내용 해시 (변경 감지용)';
