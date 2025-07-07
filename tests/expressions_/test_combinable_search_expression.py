from django.test import SimpleTestCase

from django_mongodb_backend.expressions.builtins import (
    CombinedSearchExpression,
    CompoundExpression,
    SearchEquals,
)


class CombinedSearchExpressionResolutionTest(SimpleTestCase):
    def test_combined_expression_and_or_not_resolution(self):
        A = SearchEquals(path="headline", value="A")
        B = SearchEquals(path="headline", value="B")
        C = SearchEquals(path="headline", value="C")
        D = SearchEquals(path="headline", value="D")
        expr = (~A | B) & (C | D)
        solved = CombinedSearchExpression.resolve(expr)
        self.assertIsInstance(solved, CompoundExpression)
        solved_A = CompoundExpression(must_not=[CompoundExpression(must=[A])])
        solved_B = CompoundExpression(must=[B])
        solved_C = CompoundExpression(must=[C])
        solved_D = CompoundExpression(must=[D])
        self.assertCountEqual(solved.must[0].should, [solved_A, solved_B])
        self.assertEqual(solved.must[0].minimum_should_match, 1)
        self.assertEqual(solved.must[1].should, [solved_C, solved_D])

    def test_combined_expression_de_morgans_resolution(self):
        A = SearchEquals(path="headline", value="A")
        B = SearchEquals(path="headline", value="B")
        C = SearchEquals(path="headline", value="C")
        D = SearchEquals(path="headline", value="D")
        expr = ~(A | B) & (C | D)
        solved_A = CompoundExpression(must_not=[CompoundExpression(must=[A])])
        solved_B = CompoundExpression(must_not=[CompoundExpression(must=[B])])
        solved_C = CompoundExpression(must=[C])
        solved_D = CompoundExpression(must=[D])
        solved = CombinedSearchExpression.resolve(expr)
        self.assertIsInstance(solved, CompoundExpression)
        self.assertCountEqual(solved.must[0].must, [solved_A, solved_B])
        self.assertEqual(solved.must[0].minimum_should_match, None)
        self.assertEqual(solved.must[1].should, [solved_C, solved_D])
        self.assertEqual(solved.minimum_should_match, None)

    def test_combined_expression_doble_negation(self):
        A = SearchEquals(path="headline", value="A")
        expr = ~~A
        solved = CombinedSearchExpression.resolve(expr)
        solved_A = CompoundExpression(must=[A])
        self.assertIsInstance(solved, CompoundExpression)
        self.assertEqual(solved, solved_A)

    def test_combined_expression_long_right_tree(self):
        A = SearchEquals(path="headline", value="A")
        B = SearchEquals(path="headline", value="B")
        C = SearchEquals(path="headline", value="C")
        D = SearchEquals(path="headline", value="D")
        solved_A = CompoundExpression(must=[A])
        solved_B = CompoundExpression(must_not=[CompoundExpression(must=[B])])
        solved_C = CompoundExpression(must=[C])
        solved_D = CompoundExpression(must=[D])
        expr = A & ~(B & ~(C & D))
        solved = CombinedSearchExpression.resolve(expr)
        self.assertIsInstance(solved, CompoundExpression)
        self.assertEqual(len(solved.must), 2)
        self.assertEqual(solved.must[0], solved_A)
        self.assertEqual(len(solved.must[1].should), 2)
        self.assertEqual(solved.must[1].should[0], solved_B)
        self.assertCountEqual(solved.must[1].should[1].must, [solved_C, solved_D])
        expr = A | ~(B | ~(C | D))
        solved = CombinedSearchExpression.resolve(expr)
        self.assertIsInstance(solved, CompoundExpression)
        self.assertEqual(len(solved.should), 2)
        self.assertEqual(solved.should[0], solved_A)
        self.assertEqual(len(solved.should[1].must), 2)
        self.assertEqual(solved.should[1].must[0], solved_B)
        self.assertCountEqual(solved.should[1].must[1].should, [solved_C, solved_D])
