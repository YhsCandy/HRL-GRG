#!/usr/bin/env python
import sys
sys.path.append('..')
from utils.environment import *

from worker import *
from network import *
import threading
from time import sleep
import os
import h5py

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_boolean('is_approaching_policy', False, 'If learning approaching policy.')
flags.DEFINE_integer('max_episodes', 100000, 'Maximum episodes.')
flags.DEFINE_multi_integer('max_episode_steps', [100, 200, 100, 100], 'Maximum steps for different scene types at each episode.')
flags.DEFINE_integer('max_lowlevel_episode_steps', 10,
                     'Maximum number of steps the robot can take during one episode in low-level policy.')
flags.DEFINE_integer('batch_size', 64,
                     'The size of replay memory used for training.')
flags.DEFINE_float('gamma', 0.99, 'Discount factor.')
flags.DEFINE_integer('window_size', 30, 'The size of vision window.')
flags.DEFINE_integer('vision_size', 2048, 'The size of vision feature.')
flags.DEFINE_integer('word_size', 100, 'The size of word embedding.')
flags.DEFINE_integer('score_size', 1000, 'The size of vision classification score.')
flags.DEFINE_integer('history_steps', 4, 'The number of steps need to remember during training.')
flags.DEFINE_float('highlevel_lr', 0.0001, 'Highlevel learning rate.')
flags.DEFINE_float('lowlevel_lr', 0.0007, 'Lowlevel learning rate.')
flags.DEFINE_integer('replay_start_size', 0, 'The number of observations stored in the replay buffer before training.')
flags.DEFINE_integer('skip_frames', 1, 'The times for low-level action to repeat.')
flags.DEFINE_integer('highlevel_update_freq', 100, 'Highlevel network update frequency.')
flags.DEFINE_integer('lowlevel_update_freq', 10,  'Lowlevel network update frequency.')
flags.DEFINE_integer('target_update_freq', 100000, 'Target network update frequency.')
flags.DEFINE_multi_float('epsilon', [1, 10000, 0.1], ['Initial exploration rate', 'anneal steps', 'final exploration rate'] )
flags.DEFINE_boolean('load_model', True, 'If load previous trained model or not.')
flags.DEFINE_boolean('curriculum_training', True, 'If use curriculum training or not.')
flags.DEFINE_boolean('continuing_training', False, 'If continue training or not.')
flags.DEFINE_string('pretrained_model_path', '../A3C/result_for_pretrain/model', 'The path to load pretrained model from.')
flags.DEFINE_string('model_path', './result_pretrain/model', 'The path to store or load model from.')
flags.DEFINE_integer('num_threads', 1, 'The number of threads to train one scene one target.')
flags.DEFINE_multi_string('scene_types', ["kitchen", "living_room", "bedroom", "bathroom"], 'The scene types used for training.')
flags.DEFINE_integer('num_train_scenes', 20, 'The number of scenes used for training.')
flags.DEFINE_integer('num_validate_scenes', 5, 'The number of scenes used for validation.')
flags.DEFINE_integer('num_test_scenes', 5, 'The number of scenes used for testing.')
flags.DEFINE_integer('min_step_threshold', 0, 'The number of scenes used for testing.')
flags.DEFINE_string('evaluate_file', '', '')
flags.DEFINE_boolean('is_training', False, 'If is training or not.')
flags.DEFINE_string('adjmat_path', 'gcn/selected_adjmat.mat', 'The path to the knowledge graph.')
flags.DEFINE_string('wemb_path', 'gcn/glove_map100d.hdf5', 'The path to the word embedding.')



def set_up():
    if not os.path.exists(FLAGS.model_path):
        os.makedirs(FLAGS.model_path)

    tf.reset_default_graph()
    graph = tf.Graph()
    with graph.as_default():
        global_episodes = tf.Variable(0, dtype=tf.int32, name='global_episodes', trainable=False)
        global_frames = tf.Variable(0, dtype=tf.int32, name='global_frames', trainable=False)

        lowlevel_network = Scene_Prior_Network(vision_size=FLAGS.vision_size,
                                               word_size=FLAGS.word_size,
                                               score_size=FLAGS.score_size,
                                               action_size=NUM_ACTIONS,
                                               history_steps=FLAGS.history_steps,
                                               scope='global')

        envs = []
        for scene_no in range(1, FLAGS.num_train_scenes + FLAGS.num_validate_scenes + FLAGS.num_test_scenes +1):
            for scene_type in FLAGS.scene_types:
                env = Environment(scene_type=scene_type,
                                  scene_no=scene_no,
                                  window_size=FLAGS.window_size,
                                  feature_pattern=('resnet50_2048d', 'resnet50_prob_1000d'))
                envs.append(env)

        obj_embeddings = h5py.File(FLAGS.wemb_path, 'r')

        workers = []
        for i in range(FLAGS.num_threads):
            local_lowlevel_network = Scene_Prior_Network(vision_size=FLAGS.vision_size,
                                                         word_size=FLAGS.word_size,
                                                         score_size=FLAGS.score_size,
                                                         action_size=NUM_ACTIONS,
                                                         history_steps=FLAGS.history_steps,
                                                         scope='local_%d'%i)

            worker = Worker(name=i,
                            envs=envs,
                            obj_embeddings=obj_embeddings,
                            lowlevel_networks=local_lowlevel_network,
                            global_episodes=global_episodes,
                            global_frames=global_frames)
            workers.append(worker)
        return graph, workers


def train():
    graph, workers = set_up()
    gpu_config = tf.ConfigProto()
    gpu_config.gpu_options.per_process_gpu_memory_fraction = 0.5
    gpu_config.gpu_options.allow_growth = True
    with tf.Session(graph=graph, config=gpu_config) as sess:
        coord = tf.train.Coordinator()
        all_threads = []
        for worker in workers:
            thread = threading.Thread(target=lambda: worker.work(sess))
            thread.start()
            sleep(0.1)
            all_threads.append(thread)
        thread = threading.Thread(target=lambda:workers[0].validate(sess))
        thread.start()
        sleep(0.1)
        all_threads.append(thread)
        coord.join(all_threads)



if __name__ == '__main__':
    train()