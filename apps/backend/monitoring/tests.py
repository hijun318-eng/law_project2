from django.test import TestCase

from monitoring.models import PriceConfig


class PriceConfigSeedMigrationTest(TestCase):
    """0002_seed_price_config가 신규(빈) DB에도 기본 모델 가격을 자동으로 채우는지 확인.
    TestCase는 매 테스트마다 전체 마이그레이션을 새로 적용한 테스트 DB를 쓰므로,
    실제 dev DB를 건드리지 않고 '최초 마이그레이션' 상황을 그대로 검증할 수 있다."""

    def test_default_prices_seeded(self):
        seeded = {p.model_name: p for p in PriceConfig.objects.all()}
        self.assertIn("gpt-4o-mini", seeded)
        self.assertIn("gpt-5.4-nano", seeded)
        self.assertIn("text-embedding-3-small", seeded)
        self.assertEqual(seeded["gpt-4o-mini"].prompt_token_price, 0.15)
        self.assertEqual(seeded["gpt-4o-mini"].completion_token_price, 0.60)
