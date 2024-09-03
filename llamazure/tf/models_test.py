from llamazure.tf.models import _pluralise


class TestPluralise:
	def test_empty_list(self):
		# Test case where the list is empty
		result = _pluralise("apple", [])
		expected = {"apples": []}  # Pluralised key with empty list
		assert result == expected

	def test_single_element(self):
		# Test case where the list has one element
		result = _pluralise("apple", ["apple"])
		expected = {"apple": "apple"}
		assert result == expected

	def test_multiple_elements(self):
		# Test case where the list has multiple elements
		result = _pluralise("apple", ["apple", "orange"])
		expected = {"apples": ["apple", "orange"]}
		assert result == expected

	def test_single_element_with_es_suffix(self):
		# Test case where the list has one element and uses the suffix "es"
		result = _pluralise("box", ["box"], pluralise="es")
		expected = {"box": "box"}
		assert result == expected

	def test_multiple_elements_with_es_suffix(self):
		# Test case where the list has multiple elements and uses the suffix "es"
		result = _pluralise("box", ["box", "fox"], pluralise="es")
		expected = {"boxes": ["box", "fox"]}
		assert result == expected
