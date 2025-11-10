"""
CLI Runner - Typer 기반 커맨드라인 인터페이스
"""
import typer
from typing import Optional
import time

from src.utils.playwright_launcher import PlaywrightLauncher
from src.detector.pattern_detector import PatternDetector
from src.handlers.static_toggle import StaticToggleHandler
from src.handlers.a_link import ALinkHandler
from src.handlers.function import FunctionHandler
from src.handlers.hash_routing import HashRoutingHandler
from src.handlers.api_direct import APIDirectHandler
from src.autoprofiler.auto_profiler import AutoProfiler
from src.profiles.profile_loader import ProfileLoader
from src.classifier.rule_classifier import RuleClassifier
from src.classifier.model_classifier import ModelClassifier
from src.database import get_db, init_db
from src.storage.repository import JobRepository
from src.schema import PatternType, LabelSource, CrawlResult

app = typer.Typer(help="🚀 대한민국 IT 채용공고 크롤링 시스템")


@app.command()
def crawl(
    domain: str = typer.Option(..., "--domain", help="도메인 (예: careers.example.com)"),
    base_url: str = typer.Option(..., "--base-url", help="시작 URL"),
    country: str = typer.Option("KR", "--country", help="국가 필터"),
    target: str = typer.Option("IT", "--target", help="대상 직군"),
    limit: Optional[int] = typer.Option(None, "--limit", help="수집 제한 개수"),
    auto_profile: bool = typer.Option(False, "--auto-profile", help="자동 프로파일링 활성화"),
    headless: bool = typer.Option(True, "--headless/--headed", help="헤드리스 모드")
):
    """채용공고 크롤링 실행"""
    
    typer.echo(f"\n🚀 크롤링 시작: {domain}")
    typer.echo(f"📍 URL: {base_url}")
    typer.echo(f"🎯 대상: {target} 직군")
    typer.echo(f"🌍 국가: {country}\n")
    
    start_time = time.time()
    
    # DB 초기화
    init_db()
    
    # 프로파일 로더
    profile_loader = ProfileLoader()
    profile = profile_loader.load(domain)
    
    with PlaywrightLauncher(headless=headless) as launcher:
        page = launcher.new_page(capture_network=True)
        page.goto(base_url, wait_until="networkidle")
        
        # 자동 프로파일링
        if auto_profile or not profile:
            typer.echo("🔍 자동 프로파일링 시작...")
            profiler = AutoProfiler(page, domain, launcher)
            profile = profiler.profile()
            profile_loader.save(profile)
            typer.echo(f"✅ 프로파일 생성 완료: {profile.pattern.value}\n")
        
        # 패턴 감지
        if not profile:
            detector = PatternDetector(page)
            pattern = detector.detect()
        else:
            pattern = profile.pattern
        
        typer.echo(f"🔎 탐지된 패턴: {pattern.value}")
        
        # 핸들러 선택
        handler = _get_handler(pattern, page, profile)
        
        if not handler:
            typer.echo("❌ 지원하지 않는 패턴입니다.")
            raise typer.Exit(code=1)
        
        # 크롤링 실행
        typer.echo(f"📥 크롤링 중...\n")
        postings = handler.crawl(target_category=target, limit=limit)
        
        typer.echo(f"✅ 수집 완료: {len(postings)}개 공고\n")
        
        # IT 분류
        typer.echo("🏷️  IT 직군 분류 중...")
        rule_classifier = RuleClassifier()
        # model_classifier = ModelClassifier()  # TODO: 모델 기반 분류기 구현
        
        for posting in postings:
            # 사이트에서 이미 필터링되었으면 스킵
            if posting.it_label is None:
                # 룰 기반 분류
                is_it, confidence, evidence = rule_classifier.classify(posting)
                
                posting.it_label = is_it
                posting.label_source = LabelSource.RULE
                posting.label_confidence = confidence
                posting.label_evidence = evidence
                posting.country_filter = country
        
        it_count = sum(1 for p in postings if p.it_label)
        typer.echo(f"✅ IT 직군: {it_count}/{len(postings)}개\n")
        
        # DB 저장
        typer.echo("💾 데이터베이스 저장 중...")
        with get_db() as db:
            repo = JobRepository(db)
            stats = repo.bulk_create(postings)
        
        execution_time = time.time() - start_time
        
        # 결과 출력
        typer.echo("\n" + "="*50)
        typer.echo("📊 크롤링 결과")
        typer.echo("="*50)
        typer.echo(f"도메인: {domain}")
        typer.echo(f"패턴: {pattern.value}")
        typer.echo(f"총 수집: {len(postings)}개")
        typer.echo(f"IT 필터: {it_count}개")
        typer.echo(f"저장 성공: {stats['created']}개")
        typer.echo(f"중복 스킵: {stats['duplicated']}개")
        typer.echo(f"오류: {stats['errors']}개")
        typer.echo(f"실행 시간: {execution_time:.2f}초")
        typer.echo("="*50 + "\n")


@app.command()
def list_profiles():
    """저장된 프로파일 목록"""
    loader = ProfileLoader()
    profiles = loader.list_profiles()
    
    if not profiles:
        typer.echo("📋 저장된 프로파일이 없습니다.")
        return
    
    typer.echo("\n📋 프로파일 목록\n")
    for p in profiles:
        typer.echo(f"  • {p['domain']}")
        typer.echo(f"    버전: {p['version']}")
        typer.echo(f"    패턴: {p['pattern']}")
        typer.echo(f"    검증: {p.get('last_verified', 'N/A')}\n")


@app.command()
def stats(
    domain: Optional[str] = typer.Option(None, "--domain", help="도메인 필터")
):
    """수집 통계"""
    with get_db() as db:
        repo = JobRepository(db)
        
        if domain:
            total = repo.count_by_domain(domain)
            it_count = repo.count_it_jobs(domain)
            typer.echo(f"\n📊 {domain} 통계")
        else:
            total = repo.count_all()
            it_count = repo.count_it_jobs()
            typer.echo("\n📊 전체 통계")
        
        typer.echo(f"  총 공고: {total}개")
        typer.echo(f"  IT 공고: {it_count}개")
        typer.echo(f"  비율: {it_count/total*100:.1f}%\n" if total > 0 else "  비율: N/A\n")


def _get_handler(pattern: PatternType, page, profile):
    """패턴에 맞는 핸들러 반환"""
    handler_map = {
        PatternType.STATIC_TOGGLE: StaticToggleHandler,
        PatternType.A_LINK: ALinkHandler,
        PatternType.FUNCTION: FunctionHandler,
        PatternType.HASH_ROUTING: HashRoutingHandler,
        PatternType.API_DIRECT: APIDirectHandler,
    }
    
    handler_class = handler_map.get(pattern)
    
    if handler_class:
        return handler_class(page, profile)
    
    return None


if __name__ == "__main__":
    app()
