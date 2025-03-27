import unittest

from llm_git.prompts import apply_format


class TestApplyFormat(unittest.TestCase):
    def test_simple_format(self):
        templates = [{"greeting": "Hello, {name}!"}]
        result = apply_format(templates, name="World")
        self.assertEqual(result["greeting"], "Hello, World!")

    def test_nested_format(self):
        templates = [
            {
                "greeting": "Hello, {name}!",
                "message": "{prompt[greeting]} Welcome to {place}.",
            }
        ]
        result = apply_format(templates, name="Alice", place="Wonderland")
        self.assertEqual(result["greeting"], "Hello, Alice!")
        self.assertEqual(result["message"], "Hello, Alice! Welcome to Wonderland.")

    def test_nested_format_seq(self):
        templates = [
            {"greeting": "Hello, {name}!", "foo": "bar"},
            {
                "greeting": "{prompt[greeting]} Welcome to {place}!",
            },
        ]
        result = apply_format(templates, name="Alice", place="Wonderland")
        self.assertEqual(result["greeting"], "Hello, Alice! Welcome to Wonderland!")
        self.assertEqual(result["foo"], "bar")


if __name__ == "__main__":
    unittest.main()
