import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main


class TestAiSettings(unittest.TestCase):
    def test_env_overrides_config(self):
        with mock.patch.dict(os.environ, {
            "CX_AI_API_KEY": "env-key",
            "CX_AI_BASE_URL": "http://env/v1",
            "CX_AI_MODEL": "env-model",
        }, clear=False):
            key, url, model = main.get_ai_settings({
                "api_key": "cfg-key",
                "base_url": "http://cfg/v1",
                "model": "cfg-model",
            })
        self.assertEqual((key, url, model), ("env-key", "http://env/v1", "env-model"))

    def test_config_fallback(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            key, url, model = main.get_ai_settings({
                "api_key": "cfg-key",
                "base_url": "http://cfg/v1/",
                "model": "cfg-model",
            })
        self.assertEqual(key, "cfg-key")
        self.assertEqual(url, "http://cfg/v1")
        self.assertEqual(model, "cfg-model")


class TestConfigMerge(unittest.TestCase):
    def test_nested_defaults_survive(self):
        merged = main._deep_merge(
            {"tiku_config": {"api_url": "", "thtoken": ""}, "auto_submit": False},
            {"tiku_config": {"api_url": "http://example.com"}},
        )
        self.assertEqual(merged["tiku_config"]["api_url"], "http://example.com")
        self.assertEqual(merged["tiku_config"]["thtoken"], "")
        self.assertFalse(merged["auto_submit"])


class TestAnswerCleaning(unittest.TestCase):
    def test_strip_answer_prefix(self):
        self.assertEqual(main._valid_tiku_answer("正确答案：A"), "A")

    def test_accept_dict_payload(self):
        self.assertEqual(main._valid_tiku_answer({"answer": "B"}), "B")

    def test_filter_ads_and_tokens(self):
        self.assertIsNone(main._valid_tiku_answer("请填写授权码后重试"))
        self.assertIsNone(main._valid_tiku_answer("未搜索到答案"))
        self.assertIsNone(main._valid_tiku_answer(""))

    def test_strip_html(self):
        self.assertEqual(main._valid_tiku_answer("<p>A</p>"), "A")


class TestOptionMatching(unittest.TestCase):
    OPTIONS = [
        {"key": "A", "text": "A. 硬玉"},
        {"key": "B", "text": "B. 软玉"},
        {"key": "C", "text": "C. 和田玉"},
    ]

    def test_letter(self):
        self.assertEqual(main.match_option_index("A", self.OPTIONS), 0)
        self.assertEqual(main.match_option_index("C.", self.OPTIONS), 2)

    def test_option_text(self):
        self.assertEqual(main.match_option_index("软玉", self.OPTIONS), 1)

    def test_unknown(self):
        self.assertEqual(main.match_option_index("完全无关的答案", self.OPTIONS), -1)


class TestQuestionCleanup(unittest.TestCase):
    def test_strip_number_and_type(self):
        raw = "【单选题】1. 下列属于硬玉的是（ ）（5.0分）"
        cleaned = main.clean_question_text(raw)
        self.assertNotIn("单选题", cleaned)
        self.assertNotIn("5.0分", cleaned)
        self.assertIn("硬玉", cleaned)

    def test_type_int(self):
        self.assertEqual(main._tiku_type_int("1"), 1)
        self.assertEqual(main._tiku_type_int(None), 0)


if __name__ == "__main__":
    unittest.main()
