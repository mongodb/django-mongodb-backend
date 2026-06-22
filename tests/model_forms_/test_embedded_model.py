from django.test import TestCase

from .forms import AuthorForm, BookForm, RetailerForm
from .models import Address, Author, Book, Product, Publisher, Retailer, Review


class ModelFormTests(TestCase):
    def test_update(self):
        author = Author.objects.create(
            name="Bob", age=50, address=Address(city="NYC", state="NY", zip_code="10001")
        )
        data = {
            "name": "Bob",
            "age": 51,
            "address-po_box": "",
            "address-city": "New York City",
            "address-state": "NY",
            "address-zip_code": "10001",
        }
        form = AuthorForm(data, instance=author)
        self.assertTrue(form.is_valid())
        form.save()
        author.refresh_from_db()
        self.assertEqual(author.age, 51)
        self.assertEqual(author.address.city, "New York City")

    def test_some_missing_data(self):
        author = Author.objects.create(
            name="Bob", age=50, address=Address(city="NYC", state="NY", zip_code="10001")
        )
        data = {
            "name": "Bob",
            "age": 51,
            "address-po_box": "",
            "address-city": "New York City",
            "address-state": "NY",
            "address-zip_code": "",
        }
        form = AuthorForm(data, instance=author)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["address"], ["This field is required."])

    def test_invalid_field_data(self):
        """A field's data (state) is too long."""
        author = Author.objects.create(
            name="Bob", age=50, address=Address(city="NYC", state="NY", zip_code="10001")
        )
        data = {
            "name": "Bob",
            "age": 51,
            "address-po_box": "",
            "address-city": "New York City",
            "address-state": "TOO LONG",
            "address-zip_code": "",
        }
        form = AuthorForm(data, instance=author)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["address"],
            [
                "Ensure this value has at most 2 characters (it has 8).",
                "This field is required.",
            ],
        )

    def test_all_missing_data(self):
        author = Author.objects.create(
            name="Bob", age=50, address=Address(city="NYC", state="NY", zip_code="10001")
        )
        data = {
            "name": "Bob",
            "age": 51,
            "address-po_box": "",
            "address-city": "",
            "address-state": "",
            "address-zip_code": "",
        }
        form = AuthorForm(data, instance=author)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["address"], ["This field is required."])

    def test_nullable_field(self):
        """A nullable EmbeddedModelField is removed if all fields are empty."""
        author = Author.objects.create(
            name="Bob",
            age=50,
            address=Address(city="NYC", state="NY", zip_code="10001"),
            billing_address=Address(city="NYC", state="NY", zip_code="10001"),
        )
        data = {
            "name": "Bob",
            "age": 51,
            "address-po_box": "",
            "address-city": "New York City",
            "address-state": "NY",
            "address-zip_code": "10001",
            "billing_address-po_box": "",
            "billing_address-city": "",
            "billing_address-state": "",
            "billing_address-zip_code": "",
        }
        form = AuthorForm(data, instance=author)
        self.assertTrue(form.is_valid())
        form.save()
        author.refresh_from_db()
        self.assertIsNone(author.billing_address)

    def test_rendering(self):
        form = AuthorForm()
        self.assertHTMLEqual(
            str(form.fields["address"].get_bound_field(form, "address")),
            """
            <div>
                <label for="id_address-po_box">PO Box:</label>
                <input id="id_address-po_box" maxlength="50" name="address-po_box" type="text">
            </div>
            <div>
                <label for="id_address-city">City:</label>
                <input type="text" name="address-city" maxlength="20" required id="id_address-city">
            </div>
            <div>
                <label for="id_address-state">State:</label>
                <input type="text" name="address-state" maxlength="2" required
                    id="id_address-state">
            </div>
            <div>
                <label for="id_address-zip_code">Zip code:</label>
                <input type="number" name="address-zip_code" required id="id_address-zip_code">
            </div>""",
        )


class NestedFormTests(TestCase):
    def test_update(self):
        book = Book.objects.create(
            title="Learning MongoDB",
            publisher=Publisher(
                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
            ),
        )
        data = {
            "title": "Learning MongoDB!",
            "publisher-name": "Random House!",
            "publisher-address-po_box": "",
            "publisher-address-city": "New York City",
            "publisher-address-state": "NY",
            "publisher-address-zip_code": "10001",
        }
        form = BookForm(data, instance=book)
        self.assertTrue(form.is_valid())
        form.save()
        book.refresh_from_db()
        self.assertEqual(book.title, "Learning MongoDB!")
        self.assertEqual(book.publisher.name, "Random House!")
        self.assertEqual(book.publisher.address.city, "New York City")

    def test_some_missing_data(self):
        """A required field (zip_code) is missing."""
        book = Book.objects.create(
            title="Learning MongoDB",
            publisher=Publisher(
                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
            ),
        )
        data = {
            "title": "Learning MongoDB!",
            "publisher-name": "Random House!",
            "publisher-address-po_box": "",
            "publisher-address-city": "New York City",
            "publisher-address-state": "NY",
            "publisher-address-zip_code": "",
        }
        form = BookForm(data, instance=book)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["publisher"], ["This field is required."])
        self.assertHTMLEqual(
            str(form),
            """
            <div>
              <label for="id_title">Title:</label>
              <input type="text" name="title" value="Learning MongoDB!" maxlength="50"
                required id="id_title">
            </div>
            <div>
              <fieldset>
                <legend for="id_publisher">Publisher:</legend>
                <div>
                  <label for="id_publisher-name">Name:</label>
                  <input type="text" name="publisher-name" value="Random House!" maxlength="50"
                    required id="id_publisher-name">
                </div>
                <div>
                  <fieldset>
                    <legend for="id_publisher-address">Address:</legend>
                    <div>
                      <label for="id_publisher-address-po_box">PO Box:</label>
                      <input type="text" name="publisher-address-po_box" maxlength="50"
                        id="id_publisher-address-po_box">
                    </div>
                    <div>
                      <label for="id_publisher-address-city">City:</label>
                      <input type="text" name="publisher-address-city" value="New York City"
                        maxlength="20" required id="id_publisher-address-city">
                    </div>
                    <div>
                      <label for="id_publisher-address-state">State:</label>
                      <input type="text" name="publisher-address-state" value="NY"
                        maxlength="2" required id="id_publisher-address-state">
                    </div>
                    <div>
                      <label for="id_publisher-address-zip_code">Zip code:</label>
                      <ul class="errorlist" id="id_publisher-address-zip_code_error">
                        <li>This field is required.</li>
                      </ul>
                      <input type="number" name="publisher-address-zip_code" required
                        aria-invalid="true"
                        aria-describedby="id_publisher-address-zip_code_error"
                        id="id_publisher-address-zip_code">
                    </div>
                  </fieldset>
                </div>
              </fieldset>
            </div>""",
        )

    def test_invalid_field_data(self):
        """A field's data (state) is too long."""
        book = Book.objects.create(
            title="Learning MongoDB",
            publisher=Publisher(
                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
            ),
        )
        data = {
            "title": "Learning MongoDB!",
            "publisher-name": "Random House!",
            "publisher-address-po_box": "",
            "publisher-address-city": "New York City",
            "publisher-address-state": "TOO LONG",
            "publisher-address-zip_code": "10001",
        }
        form = BookForm(data, instance=book)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["publisher"],
            ["Ensure this value has at most 2 characters (it has 8)."],
        )
        self.assertHTMLEqual(
            str(form),
            """
            <div>
              <label for="id_title">Title:</label>
              <input type="text" name="title" value="Learning MongoDB!"
                maxlength="50" required id="id_title">
            </div>
            <div>
              <fieldset>
                <legend for="id_publisher">Publisher:</legend>
                <div>
                  <label for="id_publisher-name">Name:</label>
                  <input type="text" name="publisher-name" value="Random House!"
                    maxlength="50" required id="id_publisher-name">
                </div>
                <div>
                  <fieldset>
                    <legend for="id_publisher-address">Address:</legend>
                    <div>
                      <label for="id_publisher-address-po_box">PO Box:</label>
                      <input type="text" name="publisher-address-po_box"
                        maxlength="50" id="id_publisher-address-po_box">
                    </div>
                    <div>
                      <label for="id_publisher-address-city">City:</label>
                      <input type="text" name="publisher-address-city" value="New York City"
                        maxlength="20" required id="id_publisher-address-city">
                    </div>
                    <div>
                      <label for="id_publisher-address-state">State:</label>
                      <ul class="errorlist" id="id_publisher-address-state_error">
                        <li>Ensure this value has at most 2 characters (it has 8).</li>
                      </ul>
                      <input type="text" name="publisher-address-state" value="TOO LONG"
                        maxlength="2" required aria-invalid="true"
                        aria-describedby="id_publisher-address-state_error"
                        id="id_publisher-address-state">
                    </div>
                    <div>
                      <label for="id_publisher-address-zip_code">Zip code:</label>
                      <input type="number" name="publisher-address-zip_code" value="10001"
                        required id="id_publisher-address-zip_code">
                    </div>
                  </fieldset>
                </div>
              </fieldset>
            </div>""",
        )

    def test_all_missing_data(self):
        """An embedded model missing all data triggers a required error."""
        book = Book.objects.create(
            title="Learning MongoDB",
            publisher=Publisher(
                name="Random House", address=Address(city="NYC", state="NY", zip_code="10001")
            ),
        )
        data = {
            "title": "Learning MongoDB!",
            "publisher-name": "Random House!",
            "publisher-address-po_box": "",
            "publisher-address-city": "",
            "publisher-address-state": "",
            "publisher-address-zip_code": "",
        }
        form = BookForm(data, instance=book)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["publisher"], ["This field is required."])

    def test_rendering(self):
        form = BookForm()
        self.assertHTMLEqual(
            str(form.fields["publisher"].get_bound_field(form, "publisher")),
            """
            <div>
              <label for="id_publisher-name">Name:</label>
              <input type="text" name="publisher-name" maxlength="50"
                required id="id_publisher-name">
            </div>
            <div>
              <fieldset>
                <legend for="id_publisher-address">Address:</legend>
                <div>
                  <label for="id_publisher-address-po_box">PO Box:</label>
                  <input type="text" name="publisher-address-po_box" maxlength="50"
                    id="id_publisher-address-po_box">
                </div>
                <div>
                  <label for="id_publisher-address-city">City:</label>
                  <input type="text" name="publisher-address-city" maxlength="20"
                    required id="id_publisher-address-city">
                </div>
                <div>
                  <label for="id_publisher-address-state">State:</label>
                  <input type="text" name="publisher-address-state" maxlength="2"
                    required id="id_publisher-address-state">
                </div>
                <div>
                  <label for="id_publisher-address-zip_code">Zip code:</label>
                  <input type="number" name="publisher-address-zip_code"
                    required id="id_publisher-address-zip_code">
                </div>
              </fieldset>
            </div>""",
        )


class NestedEmbeddedArrayFormTests(TestCase):
    """
    Tests for EmbeddedModelField → EmbeddedModel with EmbeddedModelArrayField
    (Retailer → Product → [Review]).
    """

    def test_create(self):
        data = {
            "name": "Acme Retail",
            "product-name": "TV",
            "product-reviews-0-title": "Great",
            "product-reviews-0-rating": "9",
            "product-reviews-TOTAL_FORMS": 2,
            "product-reviews-INITIAL_FORMS": 0,
        }
        form = RetailerForm(data)
        self.assertTrue(form.is_valid())
        retailer = form.save()
        self.assertEqual(retailer.name, "Acme Retail")
        self.assertEqual(retailer.product.name, "TV")
        self.assertEqual(len(retailer.product.reviews), 1)
        self.assertEqual(retailer.product.reviews[0].title, "Great")
        self.assertEqual(retailer.product.reviews[0].rating, 9)

    def test_update(self):
        retailer = Retailer.objects.create(
            name="Acme Retail",
            product=Product(name="TV", reviews=[Review(title="Great", rating=9)]),
        )
        data = {
            "name": "Acme Retail!",
            "product-name": "TV!",
            "product-reviews-0-title": "Great!",
            "product-reviews-0-rating": "10",
            "product-reviews-TOTAL_FORMS": 2,
            "product-reviews-INITIAL_FORMS": 1,
        }
        form = RetailerForm(data, instance=retailer)
        self.assertTrue(form.is_valid())
        form.save()
        retailer.refresh_from_db()
        self.assertEqual(retailer.name, "Acme Retail!")
        self.assertEqual(retailer.product.name, "TV!")
        self.assertEqual(len(retailer.product.reviews), 1)
        self.assertEqual(retailer.product.reviews[0].title, "Great!")
        self.assertEqual(retailer.product.reviews[0].rating, 10)

    def test_some_missing_data(self):
        """A required field (Review.title) is missing."""
        retailer = Retailer.objects.create(
            name="Acme Retail",
            product=Product(name="TV", reviews=[Review(title="Great", rating=9)]),
        )
        data = {
            "name": "Acme Retail",
            "product-name": "TV",
            "product-reviews-0-title": "",
            "product-reviews-0-rating": "9",
            "product-reviews-TOTAL_FORMS": 2,
            "product-reviews-INITIAL_FORMS": 1,
        }
        form = RetailerForm(data, instance=retailer)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["product"], ["This field is required."])

    def test_invalid_field_data(self):
        """A field's data (Review.rating) is invalid."""
        retailer = Retailer.objects.create(
            name="Acme Retail",
            product=Product(name="TV", reviews=[Review(title="Great", rating=9)]),
        )
        data = {
            "name": "Acme Retail",
            "product-name": "TV",
            "product-reviews-0-title": "Great",
            "product-reviews-0-rating": "not a number",
            "product-reviews-TOTAL_FORMS": 2,
            "product-reviews-INITIAL_FORMS": 1,
        }
        form = RetailerForm(data, instance=retailer)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["product"], ["Enter a whole number."])
        self.assertHTMLEqual(
            str(form),
            """
            <div>
              <label for="id_name">Name:</label>
              <input type="text" name="name" value="Acme Retail" maxlength="255"
                required id="id_name">
            </div>
            <div>
              <fieldset>
                <legend for="id_product">Product:</legend>
                <div>
                  <label for="id_product-name">Name:</label>
                  <input type="text" name="product-name" value="TV"
                    maxlength="255" required id="id_product-name">
                </div>
                <div>
                  <label for="id_product-reviews">Reviews:</label>
                  <table>
                    <tbody>
                      <tr>
                        <th>
                          <label for="id_product-reviews-0-title">Title:</label>
                        </th>
                        <td>
                          <input type="text" name="product-reviews-0-title"
                            value="Great" maxlength="255"
                            id="id_product-reviews-0-title">
                        </td>
                      </tr>
                      <tr>
                        <th>
                          <label for="id_product-reviews-0-rating">Rating:</label>
                        </th>
                        <td>
                          <ul class="errorlist"
                            id="id_product-reviews-0-rating_error">
                            <li>Enter a whole number.</li>
                          </ul>
                          <input type="number" name="product-reviews-0-rating"
                            value="not a number" aria-invalid="true"
                            aria-describedby="id_product-reviews-0-rating_error"
                            id="id_product-reviews-0-rating">
                        </td>
                      </tr>
                      <tr>
                        <th>
                          <label for="id_product-reviews-0-DELETE">Delete:</label>
                        </th>
                        <td>
                          <input type="checkbox" name="product-reviews-0-DELETE"
                            id="id_product-reviews-0-DELETE">
                        </td>
                      </tr>
                    </tbody>
                    <tbody>
                      <tr>
                        <th>
                          <label for="id_product-reviews-1-title">Title:</label>
                        </th>
                        <td>
                          <input type="text" name="product-reviews-1-title"
                            maxlength="255" id="id_product-reviews-1-title">
                        </td>
                      </tr>
                      <tr>
                        <th>
                          <label for="id_product-reviews-1-rating">Rating:</label>
                        </th>
                        <td>
                          <input type="number" name="product-reviews-1-rating"
                            id="id_product-reviews-1-rating">
                        </td>
                      </tr>
                      <tr>
                        <th>
                          <label for="id_product-reviews-1-DELETE">Delete:</label>
                        </th>
                        <td>
                          <input type="checkbox" name="product-reviews-1-DELETE"
                            id="id_product-reviews-1-DELETE">
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <input type="hidden" name="product-reviews-TOTAL_FORMS"
                    value="2" id="id_product-reviews-TOTAL_FORMS">
                  <input type="hidden" name="product-reviews-INITIAL_FORMS"
                    value="1" id="id_product-reviews-INITIAL_FORMS">
                  <input type="hidden" name="product-reviews-MIN_NUM_FORMS"
                    id="id_product-reviews-MIN_NUM_FORMS">
                  <input type="hidden" name="product-reviews-MAX_NUM_FORMS"
                    id="id_product-reviews-MAX_NUM_FORMS">
                </div>
              </fieldset>
            </div>""",
        )

    def test_all_missing_data(self):
        """All Review fields are empty."""
        retailer = Retailer.objects.create(
            name="Acme Retail",
            product=Product(name="TV", reviews=[Review(title="Great", rating=9)]),
        )
        data = {
            "name": "Acme Retail",
            "product-name": "TV",
            "product-reviews-0-title": "",
            "product-reviews-0-rating": "",
            "product-reviews-TOTAL_FORMS": 2,
            "product-reviews-INITIAL_FORMS": 1,
        }
        form = RetailerForm(data, instance=retailer)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["product"], ["This field is required.", "This field is required."]
        )
