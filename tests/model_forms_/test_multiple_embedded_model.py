from django.test import TestCase

from .forms import MovieForm
from .models import Movie, Review


class ModelFormTests(TestCase):
    def test_add_another(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Great!",
            "reviews-0-rating": "10",
            "reviews-1-title": "Not so great",
            "reviews-1-rating": "1",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.changed_data, ["reviews"])
        movie.refresh_from_db()
        self.assertEqual(len(movie.reviews), 2)
        review = movie.reviews[0]
        self.assertEqual(review.title, "Great!")
        self.assertEqual(review.rating, 10)
        review = movie.reviews[1]
        self.assertEqual(review.title, "Not so great")
        self.assertEqual(review.rating, 1)

    def test_update(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Not so great",
            "reviews-0-rating": "1",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertTrue(form.is_valid())
        form.save()
        movie.refresh_from_db()
        self.assertEqual(len(movie.reviews), 1)
        review = movie.reviews[0]
        self.assertEqual(review.title, "Not so great")
        self.assertEqual(review.rating, 1)

    def test_some_missing_data(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "",
            "reviews-0-rating": "1",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["reviews"], ["This field is required."])

    def test_invalid_field_data(self):
        """A field's data (rating) is invalid."""
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Great!",
            "reviews-0-rating": "not a number",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["reviews"],
            ["Enter a whole number."],
        )

    def test_all_missing_data(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "",
            "reviews-0-rating": "",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["reviews"], ["This field is required.", "This field is required."]
        )

    def test_delete(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10), Review(title="Okay", rating=5)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Not so great",
            "reviews-0-rating": "1",
            "reviews-0-DELETE": "1",
            "reviews-1-title": "Okay",
            "reviews-1-rating": "5",
            "reviews-1-DELETE": "",
            "reviews-TOTAL_FORMS": 3,
            "reviews-INITIAL_FORMS": 2,
        }
        form = MovieForm(data, instance=movie)
        self.assertTrue(form.is_valid())
        form.save()
        movie.refresh_from_db()
        self.assertEqual(len(movie.reviews), 1)
        review = movie.reviews[0]
        self.assertEqual(review.title, "Okay")
        self.assertEqual(review.rating, 5)

    def test_delete_required(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Not so great",
            "reviews-0-rating": "1",
            "reviews-0-DELETE": "1",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["reviews"], ["This field cannot be blank."])

    #    def test_nullable_field(self):
    #        """A nullable EmbeddedModelField is removed if all fields are empty."""
    #        author = Author.objects.create(
    #            name="Bob",
    #            age=50,
    #            address=Address(city="NYC", state="NY", zip_code="10001"),
    #            billing_address=Address(city="NYC", state="NY", zip_code="10001"),
    #        )
    #        data = {
    #            "name": "Bob",
    #            "age": 51,
    #            "address-po_box": "",
    #            "address-city": "New York City",
    #            "address-state": "NY",
    #            "address-zip_code": "10001",
    #            "billing_address-po_box": "",
    #            "billing_address-city": "",
    #            "billing_address-state": "",
    #            "billing_address-zip_code": "",
    #        }
    #        form = AuthorForm(data, instance=author)
    #        self.assertTrue(form.is_valid())
    #        form.save()
    #        author.refresh_from_db()
    #        self.assertIsNone(author.billing_address)

    def test_rendering(self):
        form = MovieForm()
        self.assertHTMLEqual(
            str(form.fields["reviews"].get_bound_field(form, "reviews")),
            """
            <table>
            <tbody><tr>
                <th><label for="id_reviews-0-title">Title:</label></th>
                <td>
                  <input type="text" name="reviews-0-title" maxlength="255" id="id_reviews-0-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_reviews-0-rating">Rating:</label></th>
                <td>
                  <input type="number" name="reviews-0-rating" id="id_reviews-0-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_reviews-0-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="reviews-0-DELETE" id="id_reviews-0-DELETE">
                </td>
              </tr></tbody>
            </table>
            <input type="hidden" name="reviews-TOTAL_FORMS" value="1"
                id="id_reviews-TOTAL_FORMS"><input type="hidden"
                name="reviews-INITIAL_FORMS" value="0"
                id="id_reviews-INITIAL_FORMS">
            <input type="hidden" name="reviews-MIN_NUM_FORMS" value="0"
                id="id_reviews-MIN_NUM_FORMS"><input type="hidden"
                name="reviews-MAX_NUM_FORMS" value="1000" id="id_reviews-MAX_NUM_FORMS">""",
        )


# class NestedFormTests(TestCase):
#    def test_update(self):
#        book = Book.objects.create(
#            title="Learning MongoDB",
#            publisher=Publisher(
#                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
#            ),
#        )
#        data = {
#            "title": "Learning MongoDB!",
#            "publisher-name": "Random House!",
#            "publisher-address-po_box": "",
#            "publisher-address-city": "New York City",
#            "publisher-address-state": "NY",
#            "publisher-address-zip_code": "10001",
#        }
#        form = BookForm(data, instance=book)
#        self.assertTrue(form.is_valid())
#        form.save()
#        book.refresh_from_db()
#        self.assertEqual(book.title, "Learning MongoDB!")
#        self.assertEqual(book.publisher.name, "Random House!")
#        self.assertEqual(book.publisher.address.city, "New York City")

#    def test_some_missing_data(self):
#        """A required field (zip_code) is missing."""
#        book = Book.objects.create(
#            title="Learning MongoDB",
#            publisher=Publisher(
#                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
#            ),
#        )
#        data = {
#            "title": "Learning MongoDB!",
#            "publisher-name": "Random House!",
#            "publisher-address-po_box": "",
#            "publisher-address-city": "New York City",
#            "publisher-address-state": "NY",
#            "publisher-address-zip_code": "",
#        }
#        form = BookForm(data, instance=book)
#        self.assertFalse(form.is_valid())
#        self.assertEqual(form.errors["publisher"], ["Enter all required values."])
#        self.assertHTMLEqual(
#            str(form),
#            """
#            <div>
#              <label for="id_title">Title:</label>
#              <input type="text" name="title" value="Learning MongoDB!" maxlength="50"
#                required id="id_title">
#            </div>
#            <div>
#              <fieldset>
#                <legend>Publisher:</legend>
#                <ul class="errorlist">
#                  <li>Enter all required values.</li>
#                </ul>
#                <div>
#                  <label for="id_publisher-name">Name:</label>
#                  <input type="text" name="publisher-name" value="Random House!" maxlength="50"
#                    required id="id_publisher-name">
#                </div>
#                <div>
#                  <fieldset>
#                    <legend>Address:</legend>
#                    <div>
#                      <label for="id_publisher-address-po_box">PO Box:</label>
#                      <input type="text" name="publisher-address-po_box" maxlength="50"
#                        id="id_publisher-address-po_box">
#                    </div>
#                    <div>
#                      <label for="id_publisher-address-city">City:</label>
#                      <input type="text" name="publisher-address-city" value="New York City"
#                        maxlength="20" required id="id_publisher-address-city">
#                    </div>
#                    <div>
#                      <label for="id_publisher-address-state">State:</label>
#                      <input type="text" name="publisher-address-state" value="NY"
#                        maxlength="2" required id="id_publisher-address-state">
#                    </div>
#                    <div>
#                      <label for="id_publisher-address-zip_code">Zip code:</label>
#                      <input type="number" name="publisher-address-zip_code"
#                        required id="id_publisher-address-zip_code">
#                    </div>
#                  </fieldset>
#                </div>
#              </fieldset>
#            </div>""",
#        )

#    def test_invalid_field_data(self):
#        """A field's data (state) is too long."""
#        book = Book.objects.create(
#            title="Learning MongoDB",
#            publisher=Publisher(
#                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
#            ),
#        )
#        data = {
#            "title": "Learning MongoDB!",
#            "publisher-name": "Random House!",
#            "publisher-address-po_box": "",
#            "publisher-address-city": "New York City",
#            "publisher-address-state": "TOO LONG",
#            "publisher-address-zip_code": "10001",
#        }
#        form = BookForm(data, instance=book)
#        self.assertFalse(form.is_valid())
#        self.assertEqual(
#            form.errors["publisher"],
#            ["Ensure this value has at most 2 characters (it has 8)."],
#        )
#        self.assertHTMLEqual(
#            str(form),
#            """
#            <div>
#              <label for="id_title">Title:</label>
#              <input type="text" name="title" value="Learning MongoDB!"
#                maxlength="50" required id="id_title">
#            </div>
#            <div>
#              <fieldset>
#                <legend>Publisher:</legend>
#                <ul class="errorlist">
#                  <li>Ensure this value has at most 2 characters (it has 8).</li>
#                </ul>
#                <div>
#                  <label for="id_publisher-name">Name:</label>
#                  <input type="text" name="publisher-name" value="Random House!"
#                    maxlength="50" required id="id_publisher-name">
#                </div>
#                <div>
#                  <fieldset>
#                    <legend>Address:</legend>
#                    <div>
#                      <label for="id_publisher-address-po_box">PO Box:</label>
#                      <input type="text" name="publisher-address-po_box"
#                        maxlength="50" id="id_publisher-address-po_box">
#                    </div>
#                    <div>
#                      <label for="id_publisher-address-city">City:</label>
#                      <input type="text" name="publisher-address-city" value="New York City"
#                        maxlength="20" required id="id_publisher-address-city">
#                    </div>
#                    <div>
#                      <label for="id_publisher-address-state">State:</label>
#                      <input type="text" name="publisher-address-state" value="TOO LONG"
#                        maxlength="2" required id="id_publisher-address-state">
#                    </div>
#                    <div>
#                      <label for="id_publisher-address-zip_code">Zip code:</label>
#                      <input type="number" name="publisher-address-zip_code" value="10001"
#                        required id="id_publisher-address-zip_code">
#                    </div>
#                  </fieldset>
#                </div>
#              </fieldset>
#            </div>""",
#        )

#    def test_all_missing_data(self):
#        """An embedded model with all data missing triggers a required error."""
#        book = Book.objects.create(
#            title="Learning MongoDB",
#            publisher=Publisher(
#                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
#            ),
#        )
#        data = {
#            "title": "Learning MongoDB!",
#            "publisher-name": "Random House!",
#            "publisher-address-po_box": "",
#            "publisher-address-city": "",
#            "publisher-address-state": "",
#            "publisher-address-zip_code": "",
#        }
#        form = BookForm(data, instance=book)
#        self.assertFalse(form.is_valid())
#        self.assertEqual(form.errors["publisher"], ["This field is required."])

#    def test_rendering(self):
#        form = MovieForm()
#        print(str(form.fields["reviews"].get_bound_field(form, "reviews")))
#        self.assertHTMLEqual(
#            str(form.fields["reviews"].get_bound_field(form, "reviews")),
#            """
#            <div>
#              <label for="id_publisher-name">Name:</label>
#              <input type="text" name="publisher-name" maxlength="50"
#                required id="id_publisher-name">
#            </div>
#            <div>
#              <fieldset>
#                <legend>Address:</legend>
#                <div>
#                  <label for="id_publisher-address-po_box">PO Box:</label>
#                  <input type="text" name="publisher-address-po_box" maxlength="50"
#                    id="id_publisher-address-po_box">
#                </div>
#                <div>
#                  <label for="id_publisher-address-city">City:</label>
#                  <input type="text" name="publisher-address-city" maxlength="20"
#                    required id="id_publisher-address-city">
#                </div>
#                <div>
#                  <label for="id_publisher-address-state">State:</label>
#                  <input type="text" name="publisher-address-state" maxlength="2"
#                    required id="id_publisher-address-state">
#                </div>
#                <div>
#                  <label for="id_publisher-address-zip_code">Zip code:</label>
#                  <input type="number" name="publisher-address-zip_code"
#                    required id="id_publisher-address-zip_code">
#                </div>
#              </fieldset>
#            </div>""",
#        )
