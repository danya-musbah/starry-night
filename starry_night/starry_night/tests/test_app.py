import argparse
import unittest

from starry.app import positive_int


class PositiveIntTests(unittest.TestCase):
    def test_accepts_positive_integer(self):
        self.assertEqual(positive_int("12"), 12)

    def test_rejects_zero_and_negative_values(self):
        for value in ("0", "-3"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    positive_int(value)

    def test_rejects_non_integer_values(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("many")


if __name__ == "__main__":
    unittest.main()
