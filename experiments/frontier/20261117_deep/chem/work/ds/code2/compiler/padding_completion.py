# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Apply a certified, literal completion of the twelve unused QROM rows.

Only the off-domain suffix is replaceable.  The real table is authenticated
before copying, and an active relaxed-tail search state cannot be emitted.
"""
import hashlib
import numpy as np


def apply_padding_completion(state, words):
    if 'tail_projection' in state:
        raise ValueError('Materialize the relaxed-tail search state before emission.')
    completion = state.get('padding_completion')
    if completion is None:
        return words
    if completion.get('version') != 1:
        raise ValueError('Unsupported padding-completion version.')
    if completion.get('first_unused_address') != 1220 or completion.get('word_width') != 75:
        raise ValueError('Padding completion must replace exactly addresses 1220 through 1231.')
    source = np.asarray(words)
    if source.shape != (1232, 75) or source.dtype.kind not in 'iu':
        raise ValueError('Expected a 1232 by 75 integer source word table.')
    if np.any(source < 0) or np.any(source > 255):
        raise ValueError('Source words must be bytes.')
    source = np.ascontiguousarray(source, dtype=np.uint8)
    prefix_hash = hashlib.sha256(source[:1220].tobytes()).hexdigest()
    if prefix_hash != completion.get('real_word_prefix_sha256'):
        raise ValueError('Padding completion belongs to a different real word table.')
    suffix = np.asarray(completion.get('words'))
    if suffix.shape != (12, 75) or suffix.dtype.kind not in 'iu':
        raise ValueError('Expected exactly twelve rows of 75 literal integer bytes.')
    if np.any(suffix < 0) or np.any(suffix > 255):
        raise ValueError('Padding completion contains a value outside the byte range.')
    completed = source.copy()
    completed[1220:] = suffix.astype(np.uint8)
    if not np.array_equal(completed[:1220], source[:1220]):
        raise AssertionError('Real-address prefix changed while applying padding.')
    return completed
