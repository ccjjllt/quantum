"""Reproduce explicit-P6 hybrid6 from an authenticated bundle in a fresh directory.

No repository, network, dataset, notebook execution or cached source is needed.
The input bundle retains SomeJoint's source and yoyobar carry attribution.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import sys
import threading
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def distribution_version():
    try:
        return importlib.metadata.version('kickmix')
    except importlib.metadata.PackageNotFoundError:
        # Competition-attached kickmix need not be a pip distribution.
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--cpu', type=int)
    args = parser.parse_args()
    os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    import kickmix as km
    if args.cpu is not None:
        print('cpu affinity not available on this platform; ignoring --cpu', flush=True)
    assert sha(args.bundle) == args.bundle_sha256
    bundle = json.loads(args.bundle.read_text(encoding='utf-8'))
    assert bundle['schema'] == 1 and bundle['candidate'] == 'hybrid6-guard893'
    assert (bundle['source_count'], bundle['input_count'], bundle['helper_count']) == (218,26,4)
    assert len(bundle['files']) == 248
    assert bundle['expected_native_sha256'] == 'fb2da4f299c4d41e421e5e57d07915599617291ab1c41d4e0fcefa6db1f2079c'
    started = time.perf_counter()
    peak = [0,0]
    work=args.work.resolve();work.mkdir(parents=True,exist_ok=False)
    for name,pin in bundle['files'].items():
        relative=PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts and ':' not in name and '\\' not in name
        target=work/name
        assert target.resolve().is_relative_to(work)
        data=pin['text'].encode('utf-8')
        assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256']
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(data)
        assert sha(target)==pin['sha256']
    source=work/'blocks/dqi/pro-q18-900/source'
    helpers=work/'portable_builder'
    sys.path.insert(0,str(helpers))
    sys.modules['circ']=km
    spec=importlib.util.spec_from_file_location('carry_decoder',source/'decode_best.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    # Source imports may adjust sys.path; prioritize the authenticated helper set.
    sys.path.insert(0,str(helpers))
    from transform import install
    import carry_hybrid, transform, source_utils
    for helper in (carry_hybrid,transform,source_utils):
        assert Path(helper.__file__).resolve().parent==helpers
    manager,transformation=install(module.decode,source)
    (work/'carry-source.diff').write_text(transformation.pop('source_diff'),encoding='utf-8')
    print(json.dumps(dict(stage='source_imported_and_transformed',seconds=time.perf_counter()-started)),flush=True)
    builder=km.CircuitBuilder()
    syndromes=[builder.alloc_qubits(12) for _ in range(70)]
    masks=[builder.alloc_bits(12) for _ in range(4095)]
    module.decode(builder,syndromes,masks)
    bank=manager.receipt()
    metadata=[]
    for i in range(70):
        metadata.append(f'REGISTER r{i} "S{i}"')
        metadata.extend(f'APPEND_TO_REGISTER q{12*i+k} r{i}' for k in range(12))
    for j in range(4095):
        metadata.append(f'REGISTER r{70+j} "E{j}"')
        metadata.extend(f'APPEND_TO_REGISTER b{12*j+k} r{70+j}' for k in range(12))
    circuit=km.Circuit('\n'.join(metadata))+builder.finish_circuit()
    output=work/'dqi.kmb';circuit.to_file(str(output),format='kmb')
    digest=sha(output)
    assert digest==bundle['expected_native_sha256'], 'Portable rebuild differs from admitted candidate'
    assert circuit.num_qubits==893 and len(circuit)==63176209
    for name,pin in bundle['files'].items():assert sha(work/name)==pin['sha256']
    receipt=dict(status='EXACT_PORTABLE_BUILD_PASS',candidate='hybrid6-guard893',output_sha256=digest,
        bytes=output.stat().st_size,actual_Q=circuit.num_qubits,
        static_toffoli=circuit.operation_statistics().num_toffoli_like,num_ops=len(circuit),
        bank=bank,bundle_sha256=args.bundle_sha256,script_sha256=sha(__file__),
        source_files=218,input_files=26,helper_files=4,
        source_diff_sha256=sha(work/'carry-source.diff'),
        seconds=time.perf_counter()-started,peak_rss_mib=peak[0]/2**20,peak_pss_mib=peak[1]/2**20,
        kickmix_distribution=distribution_version(),kickmix_module=km.__version__,
        cpu_affinity=None,blas_threads=1,
        scope='Exact DQI source build; official verification is a separate notebook step')
    (work/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    main()
