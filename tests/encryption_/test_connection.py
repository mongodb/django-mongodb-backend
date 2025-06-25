from .test_base import QueryableEncryptionTestCase


class TestConnection(QueryableEncryptionTestCase):
    def test_connection(self):
        # raise ImproperlyConfigured(
        #       "Encrypted fields found but "
        #       "DATABASES[[self.connection.alias}]['OPTIONS'] is missing "
        #       "auto_encryption_opts. Please set `auto_encryption_opts` "
        #       "in the connection settings."
        #   )
        pass
