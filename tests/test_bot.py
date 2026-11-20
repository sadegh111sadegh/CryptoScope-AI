import unittest

from bot import build_messages


def sample_report(important_news=None, news_available=False):
    return {
        "market": {
            "global": {},
            "coins": {"bitcoin": {}},
            "stablecoins": None,
            "defi_tvl": None,
            "fear_greed": None,
            "etf_flows": {"available": False},
            "errors": [],
        },
        "direction": "خنثی",
        "confidence": "پایین",
        "factors": [],
        "network": {},
        "technical": {"available": False, "assets": {}},
        "horizon": "داده کافی برای تخمین مدت روند نداریم.",
        "news": {"available": news_available, "items": []},
        "important_news": important_news or [],
    }


class BotReportTests(unittest.TestCase):
    def test_news_section_is_hidden_when_sources_fail(self):
        message = "\n".join(build_messages(sample_report(news_available=False)))
        self.assertNotIn("خبرهای مهم ۴۸ ساعت اخیر", message)
        self.assertNotIn("دریافت خبر از منابع ناموفق بود", message)

    def test_news_section_is_hidden_when_no_important_news_exists(self):
        message = "\n".join(build_messages(sample_report(news_available=True)))
        self.assertNotIn("خبرهای مهم ۴۸ ساعت اخیر", message)
        self.assertNotIn("خبر مهمی مطابق معیارها", message)

    def test_important_news_is_shown_with_its_headline(self):
        news = [{
            "level": "مهم",
            "category": "اقتصاد کلان",
            "title": "نمونه خبر مهم درباره نرخ بهره",
            "url": "https://example.com/news",
            "source": "example.com",
            "score": 80,
        }]
        message = "\n".join(build_messages(sample_report(news, news_available=True)))
        self.assertIn("خبرهای مهم ۴۸ ساعت اخیر", message)
        self.assertIn("نمونه خبر مهم درباره نرخ بهره", message)

    def test_generic_trading_disclaimer_is_removed(self):
        message = "\n".join(build_messages(sample_report()))
        self.assertNotIn("توصیه خریدوفروش", message)


if __name__ == "__main__":
    unittest.main()
