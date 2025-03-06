# Copyright 2025 The JAX Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from absl.testing import absltest
from absl.testing import parameterized
import jax
from jax._src import config
from jax._src import error_check
from jax._src import test_util as jtu
import jax.numpy as jnp


JaxValueError = error_check.JaxValueError


config.parse_flags_with_absl()


@jtu.with_config(jax_check_tracer_leaks=True)
class ErrorCheckTests(jtu.JaxTestCase):

  @parameterized.product(jit=[True, False])
  def test_error_check(self, jit):
    def f(x):
      error_check.set_error_if(x <= 0, "x must be greater than 0")
      return x + 1

    if jit:
      f = jax.jit(f)

    x = jnp.full((4,), -1, dtype=jnp.int32)
    f(x)
    with self.assertRaisesRegex(JaxValueError, "x must be greater than 0"):
      error_check.raise_if_error()

  @parameterized.product(jit=[True, False])
  def test_error_check_no_error(self, jit):
    def f(x):
      error_check.set_error_if(x <= 0, "x must be greater than 0")
      return x + 1

    if jit:
      f = jax.jit(f)

    x = jnp.full((4,), 1, dtype=jnp.int32)
    f(x)
    error_check.raise_if_error()  # should not raise error

  @parameterized.product(jit=[True, False])
  def test_error_check_should_report_the_first_error(self, jit):
    def f(x):
      error_check.set_error_if(x >= 1, "x must be less than 1 in f")
      return x + 1

    def g(x):
      error_check.set_error_if(x >= 1, "x must be less than 1 in g")
      return x + 1

    if jit:
      f = jax.jit(f)
      g = jax.jit(g)

    x = jnp.full((4,), 0, dtype=jnp.int32)

    x = f(x)  # check passes, so it should not set error
    x = g(x)  # check fails. so it should set error
    _ = f(x)  # check fails, but should not override the error
    with self.assertRaisesRegex(JaxValueError, "x must be less than 1 in g"):
      error_check.raise_if_error()

  @parameterized.product(jit=[True, False])
  def test_raise_if_error_clears_error(self, jit):
    def f(x):
      error_check.set_error_if(x <= 0, "x must be greater than 0 in f")
      return x + 1

    def g(x):
      error_check.set_error_if(x <= 0, "x must be greater than 0 in g")
      return x + 1

    if jit:
      f = jax.jit(f)
      g = jax.jit(g)

    x = jnp.full((4,), -1, dtype=jnp.int32)
    f(x)
    with self.assertRaisesRegex(JaxValueError, "x must be greater than 0 in f"):
      error_check.raise_if_error()

    error_check.raise_if_error()  # should not raise error

    g(x)
    with self.assertRaisesRegex(JaxValueError, "x must be greater than 0 in g"):
      error_check.raise_if_error()

  @parameterized.product(jit=[True, False])
  def test_error_check_works_with_cond(self, jit):
    def f(x):
      error_check.set_error_if(x == 0, "x must be non-zero in f")
      return x + 1

    def g(x):
      error_check.set_error_if(x == 0, "x must be non-zero in g")
      return x + 1

    def body(pred, x):
      return jax.lax.cond(pred, f, g, x)

    if jit:
      body = jax.jit(body)

    x = jnp.zeros((4,), dtype=jnp.int32)

    _ = body(jnp.bool_(True), x)
    with self.assertRaisesRegex(JaxValueError, "x must be non-zero in f"):
      error_check.raise_if_error()

    _ = body(jnp.bool_(False), x)
    with self.assertRaisesRegex(JaxValueError, "x must be non-zero in g"):
      error_check.raise_if_error()

  @parameterized.product(jit=[True, False])
  def test_error_check_works_with_while_loop(self, jit):
    def f(x):
      error_check.set_error_if(x >= 10, "x must be less than 10")
      return x + 1

    def body(x):
      return jax.lax.while_loop(lambda x: (x < 10).any(), f, x)

    if jit:
      body = jax.jit(body)

    x = jnp.arange(4, dtype=jnp.int32)
    _ = body(x)
    with self.assertRaisesRegex(JaxValueError, "x must be less than 10"):
      error_check.raise_if_error()

  @parameterized.product(jit=[True, False])
  def test_error_check_works_with_scan(self, jit):
    def f(carry, x):
      error_check.set_error_if(x >= 4, "x must be less than 4")
      return carry + x, x + 1

    def body(init, xs):
      return jax.lax.scan(f, init=init, xs=xs)

    if jit:
      body = jax.jit(body)

    init = jnp.int32(0)
    xs = jnp.arange(5, dtype=jnp.int32)
    _ = body(init, xs)
    with self.assertRaisesRegex(JaxValueError, "x must be less than 4"):
      error_check.raise_if_error()

    xs = jnp.arange(4, dtype=jnp.int32)
    _ = body(init, xs)
    error_check.raise_if_error()  # should not raise error


if __name__ == "__main__":
  absltest.main(testLoader=jtu.JaxTestLoader())
