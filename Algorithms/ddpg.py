import numpy as np
import tensorflow as tf
from Algorithms.algorithm_base import Policy


initKernelAndBias = {
    'kernel_initializer': tf.random_normal_initializer(0., .1),
    'bias_initializer': tf.constant_initializer(0.1, dtype=tf.float32)
}


class DDPG(Policy):
    def __init__(self,
                 s_dim,
                 visual_sources,
                 visual_resolutions,
                 a_dim_or_list,
                 action_type,
                 gamma=0.99,
                 ployak=0.995,
                 lr=5.0e-4,
                 max_episode=50000,
                 batch_size=100,
                 buffer_size=10000,
                 cp_dir=None,
                 log_dir=None,
                 excel_dir=None,
                 logger2file=False,
                 out_graph=False):
        super().__init__(s_dim, visual_sources, visual_resolutions, a_dim_or_list, action_type, max_episode, cp_dir, 'OFF', batch_size, buffer_size)
        self.gamma = gamma
        self.ployak = ployak
        with self.graph.as_default():
            self.lr = tf.train.polynomial_decay(lr, self.episode, self.max_episode, 1e-10, power=1.0)

            self.mu, self.action, self.actor_var = self._build_actor_net('actor', self.s, True)
            tf.identity(self.mu, 'action')
            self.target_mu, self.action_target, self.actor_target_var = self._build_actor_net('actor_target', self.s_, False)

            self.s_a = tf.concat((self.s, self.pl_a), axis=1)
            self.s_mu = tf.concat((self.s, self.mu), axis=1)
            self.s_a_target = tf.concat((self.s_, self.target_mu), axis=1)

            self.q, self.q_var = self._build_q_net('q', self.s_a, True, reuse=False)
            self.q_actor, _ = self._build_q_net('q', self.s_mu, True, reuse=True)
            self.q_target, self.q_target_var = self._build_q_net('q_target', self.s_a_target, False, reuse=False)
            self.dc_r = tf.stop_gradient(self.pl_r + self.gamma * self.q_target)

            self.q_loss = 0.5 * tf.reduce_mean(tf.squared_difference(self.q, self.dc_r))
            self.actor_loss = -tf.reduce_mean(self.q_actor)

            q_var = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='q')
            actor_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='actor')

            optimizer = tf.train.AdamOptimizer(self.lr)
            self.train_q = optimizer.minimize(
                self.q_loss, var_list=q_var + self.conv_vars, global_step=self.global_step)
            with tf.control_dependencies([self.train_q]):
                self.train_actor = optimizer.minimize(self.actor_loss, var_list=actor_vars + self.conv_vars)
            with tf.control_dependencies([self.train_actor]):
                self.assign_q_target = tf.group([tf.assign(r, self.ployak * v + (1 - self.ployak) * r) for r, v in zip(self.q_target_var, self.q_var)])
                self.assign_actor_target = tf.group([tf.assign(r, self.ployak * v + (1 - self.ployak) * r) for r, v in zip(self.actor_target_var, self.actor_var)])
            # self.assign_q_target = [tf.assign(r, 1/(self.episode+1) * v + (1-1/(self.episode+1)) * r) for r, v in zip(self.q_target_var, self.q_var)]
            # self.assign_q_target = [tf.assign(r, 1/(self.episode+1) * v + (1-1/(self.episode+1)) * r) for r, v in zip(self.actor_target_var, self.actor_var)]
            tf.summary.scalar('LOSS/actor_loss', tf.reduce_mean(self.actor_loss))
            tf.summary.scalar('LOSS/critic_loss', tf.reduce_mean(self.q_loss))
            tf.summary.scalar('LEARNING_RATE/lr', tf.reduce_mean(self.lr))
            self.summaries = tf.summary.merge_all()
            self.generate_recorder(
                cp_dir=cp_dir,
                log_dir=log_dir,
                excel_dir=excel_dir,
                logger2file=logger2file,
                graph=self.graph if out_graph else None
            )
            self.recorder.logger.info('''
　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘ　　　　　
　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘｘ　　ｘｘ　　　　　　　ｘｘｘ　　ｘｘ　　　　　
　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘｘ　　　　　　ｘｘ　　　　ｘ　　　　　
　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘｘ　　　　　　ｘｘ　　　　　　　　　　
　　　　　ｘ　　　ｘｘｘ　　　　　　　　ｘ　　　ｘｘｘ　　　　　　　　ｘｘｘｘｘｘ　　　　　　　ｘ　　　ｘｘｘｘｘ　　　
　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　　　　　　　　　　ｘｘ　　　ｘｘｘ　　　　
　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘ　　　　　　　　　　　　ｘｘ　　　　ｘ　　　　　
　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘ　　ｘｘｘ　　　　　　　　　ｘ　　　　　　　　　　　　ｘｘｘ　　ｘｘ　　　　　
　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘｘｘ　　　　　　　　ｘｘｘｘｘ　　　　　　　　　　　ｘｘｘｘｘｘ　　　　　
　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　ｘｘ　　　
            ''')
            self.init_or_restore(cp_dir)

    def _build_actor_net(self, name, input_vector, trainable):
        with tf.variable_scope(name):
            actor1 = tf.layers.dense(
                inputs=input_vector,
                units=128,
                activation=self.activation_fn,
                name='actor1',
                trainable=trainable,
                **initKernelAndBias
            )
            actor2 = tf.layers.dense(
                inputs=actor1,
                units=64,
                activation=self.activation_fn,
                name='actor2',
                trainable=trainable,
                **initKernelAndBias
            )
            mu = tf.layers.dense(
                inputs=actor2,
                units=self.a_counts,
                activation=tf.nn.tanh,
                name='mu',
                trainable=trainable,
                **initKernelAndBias
            )
            e = tf.random_normal(tf.shape(mu))
            action = tf.clip_by_value(mu + e, -1, 1)
            var = tf.get_variable_scope().global_variables()
        return mu, action, var

    def _build_q_net(self, name, input_vector, trainable, reuse=False):
        with tf.variable_scope(name):
            layer1 = tf.layers.dense(
                inputs=input_vector,
                units=256,
                activation=self.activation_fn,
                name='layer1',
                trainable=trainable,
                reuse=reuse,
                **initKernelAndBias
            )
            layer2 = tf.layers.dense(
                inputs=layer1,
                units=256,
                activation=self.activation_fn,
                name='layer2',
                trainable=trainable,
                reuse=reuse,
                **initKernelAndBias
            )
            q = tf.layers.dense(
                inputs=layer2,
                units=1,
                activation=None,
                name='q_value',
                trainable=trainable,
                reuse=reuse,
                **initKernelAndBias
            )
            var = tf.get_variable_scope().global_variables()
        return q, var

    def choose_action(self, s):
        pl_visual_s, pl_s = self.get_visual_and_vector_input(s)
        return self.sess.run(self.action, feed_dict={
            self.pl_visual_s: pl_visual_s,
            self.pl_s: pl_s,
        })

    def choose_inference_action(self, s):
        pl_visual_s, pl_s = self.get_visual_and_vector_input(s)
        return self.sess.run(self.mu, feed_dict={
            self.pl_visual_s: pl_visual_s,
            self.pl_s: pl_s,
        })

    def store_data(self, s, a, r, s_, done):
        self.off_store(s, a, r, s_, done)

    def learn(self, episode):
        s, a, r, s_, _ = self.data.sample()
        pl_visual_s, pl_s = self.get_visual_and_vector_input(s)
        pl_visual_s_, pl_s_ = self.get_visual_and_vector_input(s_)
        summaries, _ = self.sess.run([self.summaries, [self.train_q, self.train_actor, self.assign_q_target, self.assign_actor_target]], feed_dict={
            self.pl_visual_s: pl_visual_s,
            self.pl_s: pl_s,
            self.pl_a: a,
            self.pl_r: r,
            self.pl_visual_s_: pl_visual_s_,
            self.pl_s_: pl_s_,
            self.episode: episode
        })
        self.recorder.writer.add_summary(summaries, self.sess.run(self.global_step))