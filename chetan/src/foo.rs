use pyo3::prelude::*;

pub fn foo_mod(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let foo_module = PyModule::new(m.py(), "foo")?;
    
    foo_module.add_function(wrap_pyfunction!(rust_fibonacci, &foo_module)?)?;
    m.add_submodule(&foo_module)
}

#[pyfunction]
fn rust_fibonacci(n: u32) -> u128 {
    let mut a = 0;
    let mut b = 1;
    for _ in 0..n {
        let temp = a;
        a = b;
        b = temp + b;
    }
    a
}
