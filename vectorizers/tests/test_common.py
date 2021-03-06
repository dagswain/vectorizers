import pytest

from sklearn.utils.estimator_checks import check_estimator

import scipy.sparse
import numpy as np

from vectorizers import TokenCooccurrenceVectorizer
from vectorizers import NgramVectorizer
from vectorizers import SkipgramVectorizer
from vectorizers import DistributionVectorizer
from vectorizers import HistogramVectorizer
from vectorizers import KDEVectorizer

from vectorizers import SequentialDifferenceTransformer
from vectorizers import Wasserstein1DHistogramTransformer

from vectorizers.distances import kantorovich1d

from vectorizers._vectorizers import (
    ngrams_of,
    find_bin_boundaries,
    remove_node,
)
from vectorizers._window_kernels import (
    harmonic_kernel,
    triangle_kernel,
    flat_kernel,
    information_window,
)

token_data = (
    (1, 3, 1, 4, 2),
    (2, 1, 2, 3, 4, 1, 2, 1, 3, 2, 4),
    (4, 1, 1, 3, 2, 4, 2),
    (1, 2, 2, 1, 2, 1, 3, 4, 3, 2, 4),
    (3, 4, 2, 1, 3, 1, 4, 4, 1, 3, 2),
    (2, 1, 3, 1, 4, 4, 1, 4, 1, 3, 2, 4),
)

text_token_data = (
    ("foo", "pok", "foo", "wer", "bar"),
    (),
    ("bar", "foo", "bar", "pok", "wer", "foo", "bar", "foo", "pok", "bar", "wer"),
    ("wer", "foo", "foo", "pok", "bar", "wer", "bar"),
    ("foo", "bar", "bar", "foo", "bar", "foo", "pok", "wer", "pok", "bar", "wer"),
    ("pok", "wer", "bar", "foo", "pok", "foo", "wer", "wer", "foo", "pok", "bar"),
    (
        "bar",
        "foo",
        "pok",
        "foo",
        "wer",
        "wer",
        "foo",
        "wer",
        "foo",
        "pok",
        "bar",
        "wer",
    ),
)

text_token_data_permutation = (("wer", "pok"), ("bar", "pok"), ("foo", "pok", "wer"))
text_token_data_subset = (("foo", "pok"), ("pok", "foo", "foo"))
text_token_data_new_token = (("foo", "pok"), ("pok", "foo", "foo", "zaz"))

mixed_token_data = (
    (1, "pok", 1, 3.1415, "bar"),
    ("bar", 1, "bar", "pok", 3.1415, 1, "bar", 1, "pok", "bar", 3.1415),
    (3.1415, 1, 1, "pok", "bar", 3.1415, "bar"),
    (1, "bar", "bar", 1, "bar", 1, "pok", 3.1415, "pok", "bar", 3.1415),
    ("pok", 3.1415, "bar", 1, "pok", 1, 3.1415, 3.1415, 1, "pok", "bar"),
    ("bar", 1, "pok", 1, 3.1415, 3.1415, 1, 3.1415, 1, "pok", "bar", 3.1415),
)

point_data = [
    np.random.multivariate_normal(
        mean=[0.0, 0.0], cov=[[0.5, 0.0], [0.0, 0.5]], size=50
    ),
    np.random.multivariate_normal(
        mean=[0.5, 0.0], cov=[[0.5, 0.0], [0.0, 0.5]], size=60
    ),
    np.random.multivariate_normal(
        mean=[-0.5, 0.0], cov=[[0.5, 0.0], [0.0, 0.5]], size=80
    ),
    np.random.multivariate_normal(
        mean=[0.0, 0.5], cov=[[0.5, 0.0], [0.0, 0.5]], size=40
    ),
    np.random.multivariate_normal(
        mean=[0.0, -0.5], cov=[[0.5, 0.0], [0.0, 0.5]], size=20
    ),
]

value_sequence_data = [
    np.random.poisson(3.0, size=100),
    np.random.poisson(12.0, size=30),
    np.random.poisson(4.0, size=40),
    np.random.poisson(5.0, size=90),
    np.random.poisson(4.5, size=120),
    np.random.poisson(9.0, size=60),
    np.random.poisson(2.0, size=80),
]


def test_harmonic_kernel():
    kernel = harmonic_kernel([0, 0, 0, 0], 4.0)
    assert kernel[0] == 1.0
    assert kernel[-1] == 1.0 / 4.0
    assert kernel[1] == 1.0 / 2.0


def test_triangle_kernel():
    kernel = triangle_kernel([0, 0, 0, 0], 4.0)
    assert kernel[0] == 4.0
    assert kernel[-1] == 1.0
    assert kernel[1] == 3.0


def test_flat_kernel():
    kernel = flat_kernel([0] * np.random.randint(2, 10), 0.0)
    assert np.all(kernel == 1.0)


def test_ngrams_of():
    for ngram_size in (1, 2, 4):
        tokens = np.random.randint(10, size=np.random.poisson(5 + ngram_size))
        ngrams = ngrams_of(tokens, ngram_size)
        if len(tokens) >= ngram_size:
            assert len(ngrams) == len(tokens) - (ngram_size - 1)
        else:
            assert len(ngrams) == 0
        assert np.all(
            [ngrams[i][0] == tokens[i] for i in range(len(tokens) - (ngram_size - 1))]
        )
        assert np.all(
            [
                ngrams[i][-1] == tokens[i + (ngram_size - 1)]
                for i in range(len(tokens) - (ngram_size - 1))
            ]
        )


def test_find_bin_boundaries_min():
    data = np.random.poisson(5, size=1000)
    data = np.append(data, [0, 0, 0])
    bins = find_bin_boundaries(data, 10)
    # Poisson so smallest bin should be at 0
    assert bins[0] == 0.0


def test_find_boundaries_all_dupes():
    data = np.ones(100)
    with pytest.warns(UserWarning):
        bins = find_bin_boundaries(data, 10)
        assert len(bins) == 1


def test_token_cooccurrence_vectorizer_basic():
    vectorizer = TokenCooccurrenceVectorizer()
    result = vectorizer.fit_transform(token_data)
    transform = vectorizer.transform(token_data)
    assert (result != transform).nnz == 0
    assert scipy.sparse.issparse(result)
    vectorizer = TokenCooccurrenceVectorizer(
        window_radius=1, window_orientation="after"
    )
    result = vectorizer.fit_transform(token_data)
    transform = vectorizer.transform(token_data)
    assert (result != transform).nnz == 0
    assert result[0, 2] == 8
    assert result[1, 0] == 6


def test_token_cooccurrence_vectorizer_column_order():
    vectorizer = TokenCooccurrenceVectorizer().fit(text_token_data)
    vectorizer_permuted = TokenCooccurrenceVectorizer().fit(text_token_data_permutation)
    assert (
        vectorizer.column_label_dictionary_
        == vectorizer_permuted.column_label_dictionary_
    )


def test_token_cooccurrence_vectorizer_transform():
    vectorizer = TokenCooccurrenceVectorizer()
    result = vectorizer.fit_transform(text_token_data_subset)
    transform = vectorizer.transform(text_token_data)
    assert result.shape == transform.shape
    assert transform[0, 0] == 34


def test_token_cooccurence_vectorizer_transform_new_vocab():
    vectorizer = TokenCooccurrenceVectorizer()
    result = vectorizer.fit_transform(text_token_data_subset)
    transform = vectorizer.transform(text_token_data_new_token)
    assert (result != transform).nnz == 0


def test_token_cooccurrence_vectorizer_text():
    vectorizer = TokenCooccurrenceVectorizer()
    result = vectorizer.fit_transform(text_token_data)
    assert scipy.sparse.issparse(result)
    transform = vectorizer.transform(text_token_data)
    assert (result != transform).nnz == 0
    vectorizer = TokenCooccurrenceVectorizer(
        window_radius=1, window_orientation="after"
    )
    result = vectorizer.fit_transform(text_token_data)
    transform = vectorizer.transform(text_token_data)
    assert (result != transform).nnz == 0
    assert result[1, 2] == 8
    assert result[0, 1] == 6


def test_token_cooccurrence_vectorizer_fixed_tokens():
    vectorizer = TokenCooccurrenceVectorizer(token_dictionary={1: 0, 2: 1, 3: 2})
    result = vectorizer.fit_transform(token_data)
    assert scipy.sparse.issparse(result)
    vectorizer = TokenCooccurrenceVectorizer(
        window_radius=1, window_orientation="after"
    )
    result = vectorizer.fit_transform(token_data)
    assert result[0, 2] == 8
    assert result[1, 0] == 6


def test_token_cooccurrence_vectorizerexcessive_prune():
    vectorizer = TokenCooccurrenceVectorizer(min_frequency=1.0)
    with pytest.raises(ValueError):
        result = vectorizer.fit_transform(token_data)


def test_token_cooccurrence_vectorizer_min_occur():
    vectorizer = TokenCooccurrenceVectorizer(min_occurrences=3)
    result = vectorizer.fit_transform(token_data)
    assert scipy.sparse.issparse(result)
    vectorizer = TokenCooccurrenceVectorizer(
        window_radius=1, window_orientation="after"
    )
    result = vectorizer.fit_transform(token_data)
    assert result[0, 2] == 8
    assert result[1, 0] == 6


def test_token_cooccurrence_vectorizer_max_freq():
    vectorizer = TokenCooccurrenceVectorizer(max_frequency=0.2)
    result = vectorizer.fit_transform(token_data)
    assert scipy.sparse.issparse(result)
    vectorizer = TokenCooccurrenceVectorizer(
        window_radius=1, window_orientation="after"
    )
    result = vectorizer.fit_transform(token_data)
    assert result[0, 2] == 8
    assert result[1, 0] == 6


def test_token_cooccurrence_vectorizer_info_window():
    vectorizer = TokenCooccurrenceVectorizer(window_function="information")
    result = vectorizer.fit_transform(token_data)
    assert scipy.sparse.issparse(result)
    vectorizer = TokenCooccurrenceVectorizer(
        window_radius=1, window_orientation="after"
    )
    result = vectorizer.fit_transform(token_data)
    assert result[0, 2] == 8
    assert result[1, 0] == 6


def test_token_cooccurrence_vectorizer_mixed():
    vectorizer = TokenCooccurrenceVectorizer()
    with pytest.raises(ValueError):
        vectorizer.fit_transform(mixed_token_data)


def test_ngram_vectorizer_basic():
    vectorizer = NgramVectorizer()
    result = vectorizer.fit_transform(token_data)
    assert scipy.sparse.issparse(result)
    transform_result = vectorizer.transform(token_data)
    assert np.all(transform_result.data == result.data)
    assert np.all(transform_result.tocoo().col == result.tocoo().col)


def test_ngram_vectorizer_text():
    vectorizer = NgramVectorizer()
    result = vectorizer.fit_transform(text_token_data)
    assert scipy.sparse.issparse(result)
    # Ensure that the empty document has an all zero row
    assert len((result[1, :]).data) == 0


def test_ngram_vectorizer_mixed():
    vectorizer = SkipgramVectorizer()
    with pytest.raises(ValueError):
        vectorizer.fit_transform(mixed_token_data)


def test_skipgram_vectorizer_basic():
    vectorizer = SkipgramVectorizer()
    result = vectorizer.fit_transform(token_data)
    assert scipy.sparse.issparse(result)
    transform_result = vectorizer.transform(token_data)
    assert np.all(transform_result.data == result.data)
    assert np.all(transform_result.tocoo().col == result.tocoo().col)


def test_skipgram_vectorizer_text():
    vectorizer = SkipgramVectorizer()
    result = vectorizer.fit_transform(text_token_data)
    assert scipy.sparse.issparse(result)
    # Ensure that the empty document has an all zero row
    assert len((result[1, :]).data) == 0


def test_skipgram_vectorizer_mixed():
    vectorizer = SkipgramVectorizer()
    with pytest.raises(ValueError):
        vectorizer.fit_transform(mixed_token_data)


def test_distribution_vectorizer_basic():
    vectorizer = DistributionVectorizer(n_components=3)
    result = vectorizer.fit_transform(point_data)
    assert result.shape == (len(point_data), 3)
    transform_result = vectorizer.transform(point_data)
    assert np.all(result == transform_result)


def test_distribution_vectorizer_bad_params():
    vectorizer = DistributionVectorizer(n_components=-1)
    with pytest.raises(ValueError):
        vectorizer.fit(point_data)
    vectorizer = DistributionVectorizer(n_components="foo")
    with pytest.raises(ValueError):
        vectorizer.fit(point_data)
    vectorizer = DistributionVectorizer()
    with pytest.raises(ValueError):
        vectorizer.fit(point_data[0])
    vectorizer = DistributionVectorizer()
    with pytest.raises(ValueError):
        vectorizer.fit(
            [np.random.uniform(size=(10, np.random.poisson(10))) for i in range(5)]
        )
    vectorizer = DistributionVectorizer()
    with pytest.raises(ValueError):
        vectorizer.fit([[[1, 2, 3], [1, 2], [1, 2, 3, 4]], [[1, 2], [1,], [1, 2, 3]]])


def test_histogram_vectorizer_basic():
    vectorizer = HistogramVectorizer(n_components=20)
    result = vectorizer.fit_transform(value_sequence_data)
    assert result.shape == (len(value_sequence_data), 20)
    transform_result = vectorizer.transform(value_sequence_data)
    assert np.all(result == transform_result)


def test_histogram_vectorizer_outlier_bins():
    vectorizer = HistogramVectorizer(n_components=20, append_outlier_bins=True)
    result = vectorizer.fit_transform(value_sequence_data)
    assert result.shape == (len(value_sequence_data), 20 + 2)
    transform_result = vectorizer.transform([[-1.0, -1.0, -1.0, 150.0]])
    assert transform_result[0][0] == 3.0
    assert transform_result[0][-1] == 1.0


def test_kde_vectorizer_basic():
    vectorizer = KDEVectorizer(n_components=20)
    result = vectorizer.fit_transform(value_sequence_data)
    assert result.shape == (len(value_sequence_data), 20)
    transform_result = vectorizer.transform(value_sequence_data)
    assert np.all(result == transform_result)


def test_seq_diff_transformer():
    transformer = SequentialDifferenceTransformer()
    result = transformer.fit_transform(value_sequence_data)
    for i in range(len(value_sequence_data)):
        assert np.allclose(
            result[i], value_sequence_data[i][1:] - value_sequence_data[i][:-1]
        )


def test_wass1d_transfomer():
    vectorizer = HistogramVectorizer()
    histogram_data = vectorizer.fit_transform(value_sequence_data)
    transformer = Wasserstein1DHistogramTransformer()
    result = transformer.fit_transform(histogram_data)
    for i in range(result.shape[0]):
        for j in range(i + 1, result.shape[0]):
            assert np.isclose(
                kantorovich1d(histogram_data[i], histogram_data[j]),
                np.sum(np.abs(result[i] - result[j])),
            )


def test_node_removal():
    graph = scipy.sparse.random(10, 10, 0.1, format="csr")
    node_to_remove = np.argmax(np.array(graph.sum(axis=0)).T[0])
    graph_less_node = remove_node(graph, node_to_remove, inplace=False)
    assert (graph != graph_less_node).sum() > 0
    with pytest.raises(ValueError):
        graph_less_node = remove_node(graph, node_to_remove, inplace=True)
    inplace_graph = graph.tolil()
    remove_node(inplace_graph, node_to_remove, inplace=True)
    assert (inplace_graph != graph_less_node).sum() == 0

    assert np.all([node_to_remove not in row for row in inplace_graph.rows])
    assert len(inplace_graph.rows[node_to_remove]) == 0

    orig_graph = graph.tolil()
    for i, row in enumerate(orig_graph.rows):
        if node_to_remove in row and i != node_to_remove:
            assert np.all(
                np.unique(np.hstack([row, orig_graph.rows[node_to_remove]]))
                == np.unique(np.hstack([inplace_graph.rows[i], [node_to_remove]]))
            )
