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


    def test_daily_trade_levels_are_shown_only_when_setup_exists(self):
        report = sample_report()
        report["technical"] = {
            "available": True,
            "assets": {
                "bitcoin": {
                    "name": "بیت‌کوین",
                    "score": 70,
                    "signal": "تمایل صعودی",
                    "timeframes": {
                        "1d": {
                            "signal": "تمایل صعودی", "rsi14": 60.0,
                            "ema20": 115.0,
                            "entry_setup": {
                                "entry": 120.0, "stop_loss": 114.0,
                                "take_profit": 132.0, "risk_reward": "1:2",
                            },
                        }
                    },
                }
            },
        }
        message = "\n".join(build_messages(report))
        self.assertIn("موقعیت ورود روزانه", message)
        self.assertIn("حد ضرر: 114.0000", message)
        self.assertIn("هدف: 132.0000", message)

    def test_daily_trade_section_is_hidden_without_setup(self):
        report = sample_report()
        report["technical"] = {
            "available": True,
            "assets": {
                "bitcoin": {
                    "name": "بیت‌کوین", "score": 10, "signal": "خنثی",
                    "timeframes": {"1d": {"signal": "خنثی", "entry_setup": None}},
                }
            },
        }
        message = "\n".join(build_messages(report))
        self.assertNotIn("موقعیت ورود روزانه", message)

    def test_missing_technical_data_is_reported_explicitly(self):
        report = sample_report()
        report["technical"]["assets"]["bitcoin"] = {
            "timeframes": {}, "errors": ["Binance timeout"]
        }
        message = "\\n".join(build_messages(report))
        self.assertIn("تحلیل تکنیکال چندتایم‌فریمی", message)
        self.assertIn("داده تکنیکال معتبر", message)
        self.assertIn("Binance timeout", message)
        self.assertIn("فعلاً موقعیت ورود", message)

    def test_partial_timeframe_data_is_shown_without_consensus(self):
        report = sample_report()
        report["technical"]["assets"]["bitcoin"] = {
            "name": "بیت‌کوین", "score": None,
            "timeframes": {
                "1d": {
                    "signal": "تمایل نزولی", "rsi14": 42.5,
                    "ema20": 65000.0, "macd_histogram": -12.0,
                }
            },
            "errors": ["4h: timeout"],
        }
        message = "\\n".join(build_messages(report))
        self.assertIn("بیت‌کوین | 1d", message)
        self.assertIn("RSI 42.5", message)
        self.assertIn("MACD منفی", message)

    def test_fear_greed_score_is_shown_and_explanation_is_hidden(self):
        report = sample_report()
        report["market"]["fear_greed"] = {"value": 15, "interpretation": "ترس شدید"}
        message = "\n".join(build_messages(report))
        self.assertIn("15/100", message)
        self.assertIn("ترس شدید", message)
        self.assertNotIn("این بخش فقط حال‌وهوای خریداران", message)

    def test_etf_explanation_and_unavailable_placeholders_are_hidden(self):
        report = sample_report()
        message = "\n".join(build_messages(report))
        self.assertNotIn("ورود پول یعنی تقاضای بیشتر", message)
        self.assertNotIn("داده ETF دریافت نشد", message)
        self.assertNotIn("داده معتبر در دسترس نیست", message)

    def test_generic_trading_disclaimer_is_removed(self):
        message = "\n".join(build_messages(sample_report()))
        self.assertNotIn("توصیه خریدوفروش", message)


if __name__ == "__main__":
    unittest.main()
