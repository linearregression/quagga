import ctypes as ct
from itertools import izip
from quagga.matrix import Matrix
from quagga.context import Context


class RmspropStep(object):
    def __init__(self, parameters, learning_rate_policy, ema_decay=0.9, epsilon=1e-6):
        self.parameters = parameters
        self.grad_sqr = []
        for p in self.parameters:
            grad_sqr = Matrix.empty_like(p)
            grad_sqr.sync_fill(0.0)
            self.grad_sqr.append(grad_sqr)
        self.learning_rate_policy = learning_rate_policy
        self.ema_decay = ema_decay
        self.epsilon = epsilon
        self.contexts = [Context(p.device_id) for p in parameters]
        self.blocking_contexts = []

    def notify(self):
        del self.blocking_contexts[:]
        learning_rate = ct.c_float(-self.learning_rate_policy.learning_rate)
        for p, gsqr, context in izip(self.parameters, self.grad_sqr, self.contexts):
            dL_dp = p.backward_matrix
            self.blocking_contexts.append(dL_dp.last_modification_context)
            # grad_sqr[t+1] = ema_decay * grad_sqr[t] + (1 - ema_decay) * dL_dp^2
            gsqr.add_scaled_hprod(context, dL_dp, dL_dp, self.ema_decay, (1.0 - self.ema_decay))
            # p[t+1] = p[t] - learning_rate * dL_dp / sqrt(grad_sqr[t+1] + epsilon)
            p.add_scaled_div_sqrt(context, learning_rate, dL_dp, gsqr, self.epsilon)