use pyo3::prelude::*;
mod foo;
use foo::foo_mod;


#[pymodule]
fn chetan(m: &Bound<'_, PyModule>) -> PyResult<()> {
    foo_mod(m)?;
    Ok(())
}
