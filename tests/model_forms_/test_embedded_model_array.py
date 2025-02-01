from django.test import TestCase

from django_mongodb_backend.forms import EmbeddedModelArrayField

from .forms import MovieForm, StoreForm
from .models import Movie, Product, Review, Store


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

    def test_no_change(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Great!",
            "reviews-0-rating": "10",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.changed_data, [])
        movie.refresh_from_db()
        self.assertEqual(len(movie.reviews), 1)
        review = movie.reviews[0]
        self.assertEqual(review.title, "Great!")
        self.assertEqual(review.rating, 10)

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
        self.assertEqual(form.changed_data, ["reviews"])
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

    def test_max_size(self):
        """
        Submitting more than the allowed number of items (three featured
        reviews for max_size=2) is prohibited.
        """
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
            featured_reviews=[Review(title="Okay", rating=5)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Not so great",
            "reviews-0-rating": "1",
            "reviews-0-DELETE": "",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
            "featured_reviews-0-title": "Okay",
            "featured_reviews-0-rating": "5",
            "featured_reviews-1-title": "Okay",
            "featured_reviews-1-rating": "5",
            "featured_reviews-2-title": "Okay",
            "featured_reviews-2-rating": "5",
            "featured_reviews-TOTAL_FORMS": 3,
            "featured_reviews-INITIAL_FORMS": 0,
        }
        form = MovieForm(data, instance=movie)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["featured_reviews"], ["Please submit at most 2 forms."])

    def test_nullable_field(self):
        """A nullable field is emptied if all rows are deleted."""
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
            featured_reviews=[Review(title="Okay", rating=5)],
        )
        data = {
            "title": "Lion King",
            "reviews-0-title": "Not so great",
            "reviews-0-rating": "1",
            "reviews-0-DELETE": "",
            "reviews-TOTAL_FORMS": 2,
            "reviews-INITIAL_FORMS": 1,
            "featured_reviews-0-title": "Okay",
            "featured_reviews-0-rating": "5",
            "featured_reviews-0-DELETE": "1",
            "featured_reviews-TOTAL_FORMS": 2,
            "featured_reviews-INITIAL_FORMS": 1,
        }
        form = MovieForm(data, instance=movie)
        self.assertTrue(form.is_valid())
        form.save()
        movie.refresh_from_db()
        self.assertEqual(len(movie.featured_reviews), 0)

    def test_rendering(self):
        form = MovieForm()
        self.assertHTMLEqual(
            str(form.fields["reviews"].get_bound_field(form, "reviews").label_tag()),
            '<label for="id_reviews">Reviews:</label>',
        )
        self.assertHTMLEqual(
            str(form.fields["reviews"].get_bound_field(form, "reviews")),
            """
<table>
<tbody>
  <tr>
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
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_reviews-1-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-1-title" maxlength="255" id="id_reviews-1-title">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-1-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-1-rating" id="id_reviews-1-rating">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-1-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-1-DELETE" id="id_reviews-1-DELETE">
    </td>
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_reviews-2-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-2-title" maxlength="255" id="id_reviews-2-title">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-2-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-2-rating" id="id_reviews-2-rating">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-2-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-2-DELETE" id="id_reviews-2-DELETE">
    </td>
  </tr>
</tbody>
</table>
<input type="hidden" name="reviews-TOTAL_FORMS" value="3"
    id="id_reviews-TOTAL_FORMS"><input type="hidden"
    name="reviews-INITIAL_FORMS" value="0"
    id="id_reviews-INITIAL_FORMS">
<input type="hidden" name="reviews-MIN_NUM_FORMS" value="0"
    id="id_reviews-MIN_NUM_FORMS"><input type="hidden"
    name="reviews-MAX_NUM_FORMS" value="1000" id="id_reviews-MAX_NUM_FORMS">""",
        )

    def test_rendering_initial(self):
        movie = Movie.objects.create(
            title="Lion King",
            reviews=[Review(title="Great!", rating=10)],
        )
        form = MovieForm(instance=movie)
        self.assertHTMLEqual(
            str(form.fields["reviews"].get_bound_field(form, "reviews")),
            """
<table>
<tbody>
  <tr>
    <th><label for="id_reviews-0-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-0-title" maxlength="255"
        id="id_reviews-0-title" value="Great!">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-0-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-0-rating"
        id="id_reviews-0-rating" value="10">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-0-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-0-DELETE" id="id_reviews-0-DELETE">
    </td>
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_reviews-1-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-1-title" maxlength="255" id="id_reviews-1-title">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-1-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-1-rating" id="id_reviews-1-rating">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-1-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-1-DELETE" id="id_reviews-1-DELETE">
    </td>
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_reviews-2-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-2-title" maxlength="255" id="id_reviews-2-title">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-2-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-2-rating" id="id_reviews-2-rating">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-2-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-2-DELETE" id="id_reviews-2-DELETE">
    </td>
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_reviews-3-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-3-title" maxlength="255" id="id_reviews-3-title">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-3-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-3-rating" id="id_reviews-3-rating">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-3-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-3-DELETE" id="id_reviews-3-DELETE">
    </td>
  </tr>
</tbody>
</table>
<input type="hidden" name="reviews-TOTAL_FORMS" value="4"
    id="id_reviews-TOTAL_FORMS"><input type="hidden"
    name="reviews-INITIAL_FORMS" value="1"
    id="id_reviews-INITIAL_FORMS">
<input type="hidden" name="reviews-MIN_NUM_FORMS" value="0"
    id="id_reviews-MIN_NUM_FORMS"><input type="hidden"
    name="reviews-MAX_NUM_FORMS" value="1000" id="id_reviews-MAX_NUM_FORMS">""",
        )

    def test_extra_forms(self):
        """The extra_forms argument specifies the number of extra forms."""

        class ExtraMovieForm(MovieForm):
            reviews = EmbeddedModelArrayField(Review, prefix="reviews", extra_forms=2)

        form = ExtraMovieForm()
        self.assertHTMLEqual(
            str(form.fields["reviews"].get_bound_field(form, "reviews")),
            """
<table>
<tbody>
  <tr>
    <th><label for="id_reviews-0-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-0-title" maxlength="255"
        id="id_reviews-0-title">
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
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_reviews-1-title">Title:</label></th>
    <td>
      <input type="text" name="reviews-1-title" maxlength="255" id="id_reviews-1-title">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-1-rating">Rating:</label></th>
    <td>
      <input type="number" name="reviews-1-rating" id="id_reviews-1-rating">
    </td>
  </tr>
  <tr>
    <th><label for="id_reviews-1-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="reviews-1-DELETE" id="id_reviews-1-DELETE">
    </td>
  </tr>
</tbody>
</table>
<input type="hidden" name="reviews-TOTAL_FORMS" value="2"
    id="id_reviews-TOTAL_FORMS"><input type="hidden"
    name="reviews-INITIAL_FORMS" value="0"
    id="id_reviews-INITIAL_FORMS">
<input type="hidden" name="reviews-MIN_NUM_FORMS" value="0"
    id="id_reviews-MIN_NUM_FORMS"><input type="hidden"
    name="reviews-MAX_NUM_FORMS" value="1000" id="id_reviews-MAX_NUM_FORMS">""",
        )


class NestedFormTests(TestCase):
    def test_update(self):
        store = Store.objects.create(
            name="Best Buy",
            products=[Product(name="TV", reviews=[Review(title="Great", rating=9)])],
        )
        data = {
            "name": "Best Buy!",
            "products-0-name": "TV!",
            "products-0-reviews-0-title": "Great!",
            "products-0-reviews-0-rating": "9",
            "products-TOTAL_FORMS": 3,
            "products-INITIAL_FORMS": 1,
            "products-0-reviews-TOTAL_FORMS": 3,
            "products-0-reviews-INITIAL_FORMS": 1,
        }
        form = StoreForm(data, instance=store)
        self.assertTrue(form.is_valid())
        form.save()
        store.refresh_from_db()
        self.assertEqual(store.name, "Best Buy!")
        self.assertEqual(store.products[0].name, "TV!")
        self.assertEqual(store.products[0].reviews[0].title, "Great!")

    def test_delete(self):
        """The "Bad" review is deleted."""
        store = Store.objects.create(
            name="Best Buy",
            products=[
                Product(
                    name="TV",
                    reviews=[
                        Review(title="Great", rating=9),
                        Review(title="Bad", rating=1),
                    ],
                )
            ],
        )
        data = {
            "name": "Best Buy",
            "products-0-name": "TV",
            "products-0-reviews-0-title": "Great",
            "products-0-reviews-0-rating": "9",
            "products-0-reviews-1-title": "Bad",
            "products-0-reviews-1-rating": "1",
            "products-0-reviews-1-DELETE": "1",
            "products-TOTAL_FORMS": 3,
            "products-INITIAL_FORMS": 1,
            "products-0-reviews-TOTAL_FORMS": 3,
            "products-0-reviews-INITIAL_FORMS": 2,
        }
        form = StoreForm(data, instance=store)
        self.assertTrue(form.is_valid())
        form.save()
        store.refresh_from_db()
        self.assertEqual(len(store.products[0].reviews), 1)
        self.assertEqual(store.products[0].reviews[0].title, "Great")

    def test_some_missing_data(self):
        """A required field (Review.title) is missing."""
        store = Store.objects.create(
            name="Best Buy",
            products=[Product(name="TV", reviews=[Review(title="Great", rating=9)])],
        )
        data = {
            "name": "Best Buy!",
            "products-0-name": "TV!",
            "products-0-reviews-0-title": "",
            "products-0-reviews-0-rating": "9",
            "products-TOTAL_FORMS": 3,
            "products-INITIAL_FORMS": 1,
            "products-0-reviews-TOTAL_FORMS": 3,
            "products-0-reviews-INITIAL_FORMS": 1,
            "products-1-reviews-TOTAL_FORMS": 3,
            "products-1-reviews-INITIAL_FORMS": 0,
            "products-2-reviews-TOTAL_FORMS": 3,
            "products-2-reviews-INITIAL_FORMS": 0,
        }
        form = StoreForm(data, instance=store)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["products"], ["This field is required."])
        self.assertHTMLEqual(
            str(form),
            """
<div>
  <label for="id_name">Name:</label>
  <input type="text" name="name" value="Best Buy!" maxlength="255" required id="id_name">
</div>
<div>
  <label for="id_products">Products:</label>
  <ul class="errorlist" id="id_products_error">
    <li>This field is required.</li>
  </ul>
  <table>
    <tbody>
      <tr>
        <th><label for="id_products-0-name">Name:</label></th>
        <td>
          <input type="text" name="products-0-name" value="TV!" maxlength="255"
           id="id_products-0-name">
        </td>
      </tr>
      <tr>
        <th><label for="id_products-0-reviews">Reviews:</label></th>
        <td>
          <ul class="errorlist" id="id_products-0-reviews_error">
            <li>This field is required.</li>
          </ul>
          <table>
            <tbody>
              <tr>
                <th><label for="id_products-0-reviews-0-title">Title:</label></th>
                <td>
                  <ul class="errorlist" id="id_products-0-reviews-0-title_error">
                    <li>This field is required.</li>
                  </ul>
                  <input type="text" name="products-0-reviews-0-title" maxlength="255"
                   aria-invalid="true" aria-describedby="id_products-0-reviews-0-title_error"
                   id="id_products-0-reviews-0-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-0-reviews-0-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-0-reviews-0-rating" value="9"
                   id="id_products-0-reviews-0-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-0-reviews-0-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-0-reviews-0-DELETE"
                   id="id_products-0-reviews-0-DELETE">
                </td>
              </tr>
            </tbody>
            <tbody>
              <tr>
                <th><label for="id_products-0-reviews-1-title">Title:</label></th>
                <td>
                  <input type="text" name="products-0-reviews-1-title" maxlength="255"
                   id="id_products-0-reviews-1-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-0-reviews-1-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-0-reviews-1-rating"
                   id="id_products-0-reviews-1-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-0-reviews-1-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-0-reviews-1-DELETE"
                   id="id_products-0-reviews-1-DELETE">
                </td>
              </tr>
            </tbody>
            <tbody>
              <tr>
                <th><label for="id_products-0-reviews-2-title">Title:</label></th>
                <td>
                  <input type="text" name="products-0-reviews-2-title" maxlength="255"
                   id="id_products-0-reviews-2-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-0-reviews-2-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-0-reviews-2-rating"
                   id="id_products-0-reviews-2-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-0-reviews-2-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-0-reviews-2-DELETE"
                   id="id_products-0-reviews-2-DELETE">
                </td>
              </tr>
            </tbody>
          </table>
          <input type="hidden" name="products-0-reviews-TOTAL_FORMS" value="3"
           id="id_products-0-reviews-TOTAL_FORMS">
          <input type="hidden" name="products-0-reviews-INITIAL_FORMS" value="1"
            id="id_products-0-reviews-INITIAL_FORMS">
          <input type="hidden" name="products-0-reviews-MIN_NUM_FORMS"
           id="id_products-0-reviews-MIN_NUM_FORMS">
          <input type="hidden" name="products-0-reviews-MAX_NUM_FORMS"
           id="id_products-0-reviews-MAX_NUM_FORMS">
        </td>
      </tr>
      <tr>
        <th><label for="id_products-0-DELETE">Delete:</label></th>
        <td>
          <input type="checkbox" name="products-0-DELETE" id="id_products-0-DELETE">
        </td>
      </tr>
    </tbody>
    <tbody>
      <tr>
        <th><label for="id_products-1-name">Name:</label></th>
        <td>
          <input type="text" name="products-1-name" maxlength="255" id="id_products-1-name">
        </td>
      </tr>
      <tr>
        <th><label for="id_products-1-reviews">Reviews:</label></th>
        <td>
          <table>
            <tbody>
              <tr>
                <th><label for="id_products-1-reviews-0-title">Title:</label></th>
                <td>
                  <input type="text" name="products-1-reviews-0-title"
                   maxlength="255" id="id_products-1-reviews-0-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-1-reviews-0-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-1-reviews-0-rating"
                   id="id_products-1-reviews-0-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-1-reviews-0-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-1-reviews-0-DELETE"
                   id="id_products-1-reviews-0-DELETE">
                </td>
              </tr>
            </tbody>
            <tbody>
              <tr>
                <th><label for="id_products-1-reviews-1-title">Title:</label></th>
                <td>
                  <input type="text" name="products-1-reviews-1-title" maxlength="255"
                   id="id_products-1-reviews-1-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-1-reviews-1-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-1-reviews-1-rating"
                   id="id_products-1-reviews-1-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-1-reviews-1-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-1-reviews-1-DELETE"
                   id="id_products-1-reviews-1-DELETE">
                </td>
              </tr>
            </tbody>
            <tbody>
              <tr>
                <th><label for="id_products-1-reviews-2-title">Title:</label></th>
                <td>
                  <input type="text" name="products-1-reviews-2-title" maxlength="255"
                   id="id_products-1-reviews-2-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-1-reviews-2-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-1-reviews-2-rating"
                   id="id_products-1-reviews-2-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-1-reviews-2-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-1-reviews-2-DELETE"
                   id="id_products-1-reviews-2-DELETE">
                </td>
              </tr>
            </tbody>
          </table>
          <input type="hidden" name="products-1-reviews-TOTAL_FORMS"
           value="3" id="id_products-1-reviews-TOTAL_FORMS">
          <input type="hidden" name="products-1-reviews-INITIAL_FORMS"
           value="0" id="id_products-1-reviews-INITIAL_FORMS">
          <input type="hidden" name="products-1-reviews-MIN_NUM_FORMS"
           id="id_products-1-reviews-MIN_NUM_FORMS">
          <input type="hidden" name="products-1-reviews-MAX_NUM_FORMS"
           id="id_products-1-reviews-MAX_NUM_FORMS">
        </td>
      </tr>
      <tr>
        <th><label for="id_products-1-DELETE">Delete:</label></th>
        <td>
          <input type="checkbox" name="products-1-DELETE" id="id_products-1-DELETE">
        </td>
      </tr>
    </tbody>
    <tbody>
      <tr>
        <th><label for="id_products-2-name">Name:</label></th>
        <td>
          <input type="text" name="products-2-name" maxlength="255" id="id_products-2-name">
        </td>
      </tr>
      <tr>
        <th><label for="id_products-2-reviews">Reviews:</label></th>
        <td>
          <table>
            <tbody>
              <tr>
                <th><label for="id_products-2-reviews-0-title">Title:</label></th>
                <td>
                  <input type="text" name="products-2-reviews-0-title" maxlength="255"
                   id="id_products-2-reviews-0-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-2-reviews-0-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-2-reviews-0-rating"
                   id="id_products-2-reviews-0-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-2-reviews-0-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-2-reviews-0-DELETE"
                   id="id_products-2-reviews-0-DELETE">
                </td>
              </tr>
            </tbody>
            <tbody>
              <tr>
                <th><label for="id_products-2-reviews-1-title">Title:</label></th>
                <td>
                  <input type="text" name="products-2-reviews-1-title" maxlength="255"
                   id="id_products-2-reviews-1-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-2-reviews-1-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-2-reviews-1-rating"
                   id="id_products-2-reviews-1-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-2-reviews-1-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-2-reviews-1-DELETE"
                   id="id_products-2-reviews-1-DELETE">
                </td>
              </tr>
            </tbody>
            <tbody>
              <tr>
                <th><label for="id_products-2-reviews-2-title">Title:</label></th>
                <td>
                  <input type="text" name="products-2-reviews-2-title" maxlength="255"
                   id="id_products-2-reviews-2-title">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-2-reviews-2-rating">Rating:</label></th>
                <td>
                  <input type="number" name="products-2-reviews-2-rating"
                   id="id_products-2-reviews-2-rating">
                </td>
              </tr>
              <tr>
                <th><label for="id_products-2-reviews-2-DELETE">Delete:</label></th>
                <td>
                  <input type="checkbox" name="products-2-reviews-2-DELETE"
                   id="id_products-2-reviews-2-DELETE">
                </td>
              </tr>
            </tbody>
          </table>
          <input type="hidden" name="products-2-reviews-TOTAL_FORMS"
           value="3" id="id_products-2-reviews-TOTAL_FORMS">
          <input type="hidden" name="products-2-reviews-INITIAL_FORMS"
           value="0" id="id_products-2-reviews-INITIAL_FORMS">
          <input type="hidden" name="products-2-reviews-MIN_NUM_FORMS"
           id="id_products-2-reviews-MIN_NUM_FORMS">
          <input type="hidden" name="products-2-reviews-MAX_NUM_FORMS"
           id="id_products-2-reviews-MAX_NUM_FORMS">
        </td>
      </tr>
      <tr>
        <th><label for="id_products-2-DELETE">Delete:</label></th>
        <td>
          <input type="checkbox" name="products-2-DELETE" id="id_products-2-DELETE">
        </td>
      </tr>
    </tbody>
  </table>
  <input type="hidden" name="products-TOTAL_FORMS" value="3" id="id_products-TOTAL_FORMS">
  <input type="hidden" name="products-INITIAL_FORMS" value="1" id="id_products-INITIAL_FORMS">
  <input type="hidden" name="products-MIN_NUM_FORMS" id="id_products-MIN_NUM_FORMS">
  <input type="hidden" name="products-MAX_NUM_FORMS" id="id_products-MAX_NUM_FORMS">
</div>""",
        )

    def test_invalid_field_data(self):
        """A field's data (Review.title) is too long."""
        data = {
            "name": "Best Buy!",
            "products-0-name": "TV!",
            "products-0-reviews-0-title": "A" * 256,
            "products-0-reviews-0-rating": "9",
            "products-TOTAL_FORMS": 3,
            "products-INITIAL_FORMS": 1,
            "products-0-reviews-TOTAL_FORMS": 3,
            "products-0-reviews-INITIAL_FORMS": 1,
            "products-1-reviews-TOTAL_FORMS": 3,
            "products-1-reviews-INITIAL_FORMS": 0,
            "products-2-reviews-TOTAL_FORMS": 3,
            "products-2-reviews-INITIAL_FORMS": 0,
        }
        form = StoreForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["products"],
            ["Ensure this value has at most 255 characters (it has 256)."],
        )

    def test_all_missing_data(self):
        """
        An embedded model array field (reviews) with all data missing triggers
        a required error.
        """
        store = Store.objects.create(
            name="Best Buy",
            products=[Product(name="TV", reviews=[Review(title="Great", rating=9)])],
        )
        data = {
            "name": "Best Buy!",
            "products-0-name": "TV!",
            "products-0-reviews-0-title": "",
            "products-0-reviews-0-rating": "",
            "products-TOTAL_FORMS": 3,
            "products-INITIAL_FORMS": 1,
            "products-0-reviews-TOTAL_FORMS": 3,
            "products-0-reviews-INITIAL_FORMS": 1,
            "products-1-reviews-TOTAL_FORMS": 3,
            "products-1-reviews-INITIAL_FORMS": 0,
            "products-2-reviews-TOTAL_FORMS": 3,
            "products-2-reviews-INITIAL_FORMS": 0,
        }
        form = StoreForm(data, instance=store)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["products"], ["This field is required.", "This field is required."]
        )

    def test_rendering(self):
        form = StoreForm()
        self.assertHTMLEqual(
            str(form.fields["products"].get_bound_field(form, "products")),
            """
<table>
<tbody>
  <tr>
    <th><label for="id_products-0-name">Name:</label></th>
    <td>
      <input type="text" name="products-0-name" maxlength="255" id="id_products-0-name">
    </td>
  </tr>
  <tr>
    <th><label for="id_products-0-reviews">Reviews:</label></th>
    <td>
      <table>
        <tbody>
          <tr>
            <th><label for="id_products-0-reviews-0-title">Title:</label></th>
            <td>
              <input type="text" name="products-0-reviews-0-title" maxlength="255"
               id="id_products-0-reviews-0-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-0-reviews-0-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-0-reviews-0-rating"
               id="id_products-0-reviews-0-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-0-reviews-0-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-0-reviews-0-DELETE"
               id="id_products-0-reviews-0-DELETE">
            </td>
          </tr>
        </tbody>
        <tbody>
          <tr>
            <th><label for="id_products-0-reviews-1-title">Title:</label></th>
            <td>
              <input type="text" name="products-0-reviews-1-title" maxlength="255"
               id="id_products-0-reviews-1-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-0-reviews-1-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-0-reviews-1-rating"
               id="id_products-0-reviews-1-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-0-reviews-1-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-0-reviews-1-DELETE"
               id="id_products-0-reviews-1-DELETE">
            </td>
          </tr>
        </tbody>
        <tbody>
          <tr>
            <th><label for="id_products-0-reviews-2-title">Title:</label></th>
            <td>
              <input type="text" name="products-0-reviews-2-title" maxlength="255"
               id="id_products-0-reviews-2-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-0-reviews-2-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-0-reviews-2-rating"
               id="id_products-0-reviews-2-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-0-reviews-2-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-0-reviews-2-DELETE"
               id="id_products-0-reviews-2-DELETE">
            </td>
          </tr>
        </tbody>
      </table>
      <input type="hidden" name="products-0-reviews-TOTAL_FORMS" value="3"
       id="id_products-0-reviews-TOTAL_FORMS"><input type="hidden"
       name="products-0-reviews-INITIAL_FORMS" value="0"
       id="id_products-0-reviews-INITIAL_FORMS">
     <input type="hidden" name="products-0-reviews-MIN_NUM_FORMS" value="0"
       id="id_products-0-reviews-MIN_NUM_FORMS">
       <input type="hidden" name="products-0-reviews-MAX_NUM_FORMS"
         value="1000" id="id_products-0-reviews-MAX_NUM_FORMS">
    </td>
  </tr>
  <tr>
    <th><label for="id_products-0-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="products-0-DELETE" id="id_products-0-DELETE">
    </td>
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_products-1-name">Name:</label></th>
    <td>
      <input type="text" name="products-1-name" maxlength="255" id="id_products-1-name">
    </td>
  </tr>
  <tr>
    <th><label for="id_products-1-reviews">Reviews:</label></th>
    <td>
      <table>
        <tbody>
          <tr>
            <th><label for="id_products-1-reviews-0-title">Title:</label></th>
            <td>
              <input type="text" name="products-1-reviews-0-title" maxlength="255"
               id="id_products-1-reviews-0-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-1-reviews-0-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-1-reviews-0-rating"
               id="id_products-1-reviews-0-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-1-reviews-0-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-1-reviews-0-DELETE"
               id="id_products-1-reviews-0-DELETE">
            </td>
          </tr>
        </tbody>
        <tbody>
          <tr>
            <th><label for="id_products-1-reviews-1-title">Title:</label></th>
            <td>
              <input type="text" name="products-1-reviews-1-title" maxlength="255"
               id="id_products-1-reviews-1-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-1-reviews-1-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-1-reviews-1-rating"
               id="id_products-1-reviews-1-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-1-reviews-1-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-1-reviews-1-DELETE"
               id="id_products-1-reviews-1-DELETE">
            </td>
          </tr>
        </tbody>
        <tbody>
          <tr>
            <th><label for="id_products-1-reviews-2-title">Title:</label></th>
            <td>
              <input type="text" name="products-1-reviews-2-title" maxlength="255"
               id="id_products-1-reviews-2-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-1-reviews-2-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-1-reviews-2-rating"
               id="id_products-1-reviews-2-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-1-reviews-2-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-1-reviews-2-DELETE"
               id="id_products-1-reviews-2-DELETE">
            </td>
          </tr>
        </tbody>
      </table>
      <input type="hidden" name="products-1-reviews-TOTAL_FORMS" value="3"
       id="id_products-1-reviews-TOTAL_FORMS"><input type="hidden"
       name="products-1-reviews-INITIAL_FORMS" value="0"
       id="id_products-1-reviews-INITIAL_FORMS">
     <input type="hidden" name="products-1-reviews-MIN_NUM_FORMS" value="0"
       id="id_products-1-reviews-MIN_NUM_FORMS">
       <input type="hidden" name="products-1-reviews-MAX_NUM_FORMS"
         value="1000" id="id_products-1-reviews-MAX_NUM_FORMS">
    </td>
  </tr>
  <tr>
    <th><label for="id_products-1-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="products-1-DELETE" id="id_products-1-DELETE">
    </td>
  </tr>
</tbody>
<tbody>
  <tr>
    <th><label for="id_products-2-name">Name:</label></th>
    <td>
      <input type="text" name="products-2-name" maxlength="255" id="id_products-2-name">
    </td>
  </tr>
  <tr>
    <th><label for="id_products-2-reviews">Reviews:</label></th>
    <td>
      <table>
        <tbody>
          <tr>
            <th><label for="id_products-2-reviews-0-title">Title:</label></th>
            <td>
              <input type="text" name="products-2-reviews-0-title" maxlength="255"
               id="id_products-2-reviews-0-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-2-reviews-0-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-2-reviews-0-rating"
               id="id_products-2-reviews-0-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-2-reviews-0-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-2-reviews-0-DELETE"
               id="id_products-2-reviews-0-DELETE">
            </td>
          </tr>
        </tbody>
        <tbody>
          <tr>
            <th><label for="id_products-2-reviews-1-title">Title:</label></th>
            <td>
              <input type="text" name="products-2-reviews-1-title" maxlength="255"
               id="id_products-2-reviews-1-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-2-reviews-1-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-2-reviews-1-rating"
               id="id_products-2-reviews-1-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-2-reviews-1-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-2-reviews-1-DELETE"
               id="id_products-2-reviews-1-DELETE">
            </td>
          </tr>
        </tbody>
        <tbody>
          <tr>
            <th><label for="id_products-2-reviews-2-title">Title:</label></th>
            <td>
              <input type="text" name="products-2-reviews-2-title" maxlength="255"
               id="id_products-2-reviews-2-title">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-2-reviews-2-rating">Rating:</label></th>
            <td>
              <input type="number" name="products-2-reviews-2-rating"
               id="id_products-2-reviews-2-rating">
            </td>
          </tr>
          <tr>
            <th><label for="id_products-2-reviews-2-DELETE">Delete:</label></th>
            <td>
              <input type="checkbox" name="products-2-reviews-2-DELETE"
               id="id_products-2-reviews-2-DELETE">
            </td>
          </tr>
        </tbody>
      </table>
      <input type="hidden" name="products-2-reviews-TOTAL_FORMS" value="3"
       id="id_products-2-reviews-TOTAL_FORMS"><input type="hidden"
       name="products-2-reviews-INITIAL_FORMS" value="0"
       id="id_products-2-reviews-INITIAL_FORMS">
     <input type="hidden" name="products-2-reviews-MIN_NUM_FORMS" value="0"
       id="id_products-2-reviews-MIN_NUM_FORMS">
       <input type="hidden" name="products-2-reviews-MAX_NUM_FORMS"
         value="1000" id="id_products-2-reviews-MAX_NUM_FORMS">
    </td>
  </tr>
  <tr>
    <th><label for="id_products-2-DELETE">Delete:</label></th>
    <td>
      <input type="checkbox" name="products-2-DELETE" id="id_products-2-DELETE">
    </td>
  </tr>
</tbody>
</table>
<input type="hidden" name="products-TOTAL_FORMS" value="3"
id="id_products-TOTAL_FORMS"><input type="hidden" name="products-INITIAL_FORMS"
value="0" id="id_products-INITIAL_FORMS">
<input type="hidden" name="products-MIN_NUM_FORMS" value="0" id="id_products-MIN_NUM_FORMS">
<input type="hidden" name="products-MAX_NUM_FORMS" value="1000" id="id_products-MAX_NUM_FORMS">""",
        )
