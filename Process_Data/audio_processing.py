#!/usr/bin/env python
# encoding: utf-8
import os
import pathlib
import traceback
import random
import librosa
import numpy as np
import soundfile as sf
import torch
import torch.nn.utils.rnn as rnn_utils
from pydub import AudioSegment
from python_speech_features import fbank, delta, sigproc
from scipy import signal
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
from speechpy.feature import mfe
from speechpy.processing import cmvn, cmvnw

from Process_Data import constants as c
from Process_Data.Compute_Feat.compute_vad import ComputeVadEnergy
from Process_Data.xfcc.common import local_fbank, local_mfcc


def mk_MFB(filename, sample_rate=c.SAMPLE_RATE, use_delta=c.USE_DELTA, use_scale=c.USE_SCALE, use_logscale=c.USE_LOGSCALE):
    audio, sr = librosa.load(filename, sr=sample_rate, mono=True)
    #audio = audio.flatten()

    filter_banks, energies = fbank(audio, samplerate=sample_rate, nfilt=c.FILTER_BANK, winlen=0.025)

    if use_logscale:
        filter_banks = 20 * np.log10(np.maximum(filter_banks, 1e-5))

    if use_delta:
        delta_1 = delta(filter_banks, N=1)
        delta_2 = delta(delta_1, N=1)

        filter_banks = normalize_frames(filter_banks, Scale=use_scale)
        delta_1 = normalize_frames(delta_1, Scale=use_scale)
        delta_2 = normalize_frames(delta_2, Scale=use_scale)

        frames_features = np.hstack([filter_banks, delta_1, delta_2])
    else:
        filter_banks = normalize_frames(filter_banks, Scale=use_scale)
        frames_features = filter_banks

    np.save(filename.replace('.wav', '.npy'), frames_features)

    return


def resample_wav(in_wav, out_wav, sr):
    try:
        samples, samplerate = sf.read(in_wav, dtype='float32')
        samples = np.asfortranarray(samples)
        samples = librosa.resample(samples, samplerate, sr)

        sf.write(file=out_wav, data=samples, samplerate=sr, format='WAV')
    except Exception as e:
        traceback.print_exc()
        raise (e)


def butter_bandpass(cutoff, fs, order=15):
    nyq = 0.5 * fs
    sos = butter(order, np.array(cutoff) / nyq, btype='bandpass', analog=False, output='sos')
    return sos


def butter_bandpass_filter(data, cutoff, fs, order=15):
    int2float = False
    if data.dtype == np.int16:
        data = data / 32768.
        data = data.astype(np.float32)
        int2float = True

    sos = butter_bandpass(cutoff, fs, order=order)
    y = sosfilt(sos, data)

    if int2float:
        y = (y * 32768).astype(np.int16)
    return y  # Filter requirements.

def make_Fbank(filename, write_path,  # sample_rate=c.SAMPLE_RATE,
               use_delta=c.USE_DELTA,
               use_scale=c.USE_SCALE,
               nfilt=c.FILTER_BANK,
               use_logscale=c.USE_LOGSCALE,
               use_energy=c.USE_ENERGY,
               normalize=c.NORMALIZE):

    if not os.path.exists(filename):
        raise ValueError('wav file does not exist.')

    sample_rate, audio = wavfile.read(filename)
    # audio, sr = librosa.load(filename, sr=None, mono=True)
    #audio = audio.flatten()
    filter_banks, energies = fbank(audio,
                                   samplerate=sample_rate,
                                   nfilt=nfilt,
                                   winlen=0.025,
                                   winfunc=np.hamming)

    if use_energy:
        energies = energies.reshape(energies.shape[0], 1)
        filter_banks = np.concatenate((energies, filter_banks), axis=1)
        # frames_features[:, 0] = np.log(energies)

    if use_logscale:
        # filter_banks = 20 * np.log10(np.maximum(filter_banks, 1e-5))
        filter_banks = np.log(np.maximum(filter_banks, 1e-5))

    # Todo: extract the normalize step?
    if use_delta:
        delta_1 = delta(filter_banks, N=1)
        delta_2 = delta(delta_1, N=1)

        filter_banks = normalize_frames(filter_banks, Scale=use_scale)
        delta_1 = normalize_frames(delta_1, Scale=use_scale)
        delta_2 = normalize_frames(delta_2, Scale=use_scale)

        filter_banks = np.hstack([filter_banks, delta_1, delta_2])

    if normalize:
        filter_banks = normalize_frames(filter_banks, Scale=use_scale)

    frames_features = filter_banks

    file_path = pathlib.Path(write_path)
    if not file_path.parent.exists():
        os.makedirs(str(file_path.parent))

    np.save(write_path, frames_features)

    # np.save(filename.replace('.wav', '.npy'), frames_features)
    return

def compute_fbank_feat(filename, nfilt=c.FILTER_BANK, use_logscale=c.USE_LOGSCALE, use_energy=True, add_energy=True, normalize=c.CMVN, vad=c.VAD):
    """
    Making feats more like in kaldi.

    :param filename:
    :param use_delta:
    :param nfilt:
    :param use_logscale:
    :param use_energy:
    :param normalize:
    :return:
    """

    if not os.path.exists(filename):
        raise ValueError('Wav file does not exist.')

    sample_rate, audio = wavfile.read(filename)
    pad_size = np.ceil((len(audio) - 0.025 * sample_rate) / (0.01 * sample_rate)) * 0.01 * sample_rate - len(audio) + 0.025 * sample_rate

    audio = np.lib.pad(audio, (0, int(pad_size)), 'symmetric')

    filter_banks, energies = mfe(audio, sample_rate, frame_length=0.025, frame_stride=0.01, num_filters=nfilt, fft_length=512, low_frequency=0, high_frequency=None)

    if use_energy:
        if add_energy:
            # Add an extra dimension to features
            energies = energies.reshape(energies.shape[0], 1)
            filter_banks = np.concatenate((energies, filter_banks), axis=1)
        else:
            # replace the 1st dim as energy
            energies = energies.reshape(energies.shape[0], 1)
            filter_banks[:, 0]=energies[:, 0]

    if use_logscale:
        filter_banks = np.log(np.maximum(filter_banks, 1e-5))
        # filter_banks = np.log(filter_banks)

    if normalize=='cmvn':
        # vec(array): input_feature_matrix (size:(num_observation, num_features))
        norm_fbank = cmvn(vec=filter_banks, variance_normalization=True)
    elif normalize=='cmvnw':
        norm_fbank = cmvnw(vec=filter_banks, win_size=301, variance_normalization=True)

    if use_energy and vad:
        voiced = []
        ComputeVadEnergy(filter_banks, voiced)
        voiced = np.array(voiced)
        voiced_index = np.argwhere(voiced==1).squeeze()
        norm_fbank = norm_fbank[voiced_index]

        return norm_fbank, voiced

    return norm_fbank


def GenerateSpect(wav_path, write_path, windowsize=25, stride=10, nfft=c.NUM_FFT):
    """
    Pre-computing spectrograms for wav files
    :param wav_path: path of the wav file
    :param write_path: where to write the spectrogram .npy file
    :param windowsize:
    :param stride:
    :param nfft:
    :return: None
    """
    if not os.path.exists(wav_path):
        raise ValueError('wav file does not exist.')
    #pdb.set_trace()

    # samples, sample_rate = wavfile.read(wav_path)
    sample_rate, samples = sf.read(wav_path, dtype='int16')
    sample_rate_norm = int(sample_rate / 1e3)
    frequencies, times, spectrogram = signal.spectrogram(x=samples, fs=sample_rate, window=signal.hamming(windowsize * sample_rate_norm), noverlap=(windowsize-stride) * sample_rate_norm, nfft=nfft)

    # Todo: store the whole spectrogram
    # spectrogram = spectrogram[:, :300]
    # while spectrogram.shape[1]<300:
    #     # Copy padding
    #     spectrogram = np.concatenate((spectrogram, spectrogram), axis=1)
    #
    #     # raise ValueError("The dimension of spectrogram is less than 300")
    # spectrogram = spectrogram[:, :300]
    # maxCol = np.max(spectrogram,axis=0)
    # spectrogram = np.nan_to_num(spectrogram / maxCol)
    # spectrogram = spectrogram * 255
    # spectrogram = spectrogram.astype(np.uint8)

    # For voxceleb1
    # file_path = wav_path.replace('Data/voxceleb1', 'Data/voxceleb1')
    # file_path = file_path.replace('.wav', '.npy')

    file_path = pathlib.Path(write_path)
    if not file_path.parent.exists():
        os.makedirs(str(file_path.parent))

    np.save(write_path, spectrogram)

    # return spectrogram


def Make_Spect(wav_path, windowsize, stride, window=np.hamming,
               bandpass=False, lowfreq=0, highfreq=0, log_scale=True,
               preemph=0.97, duration=False, nfft=None, normalize=False):
    """
    read wav as float type. [-1.0 ,1.0]
    :param wav_path:
    :param windowsize:
    :param stride:
    :param window: default to np.hamming
    :return: return spectrogram with shape of (len(wav/stride), windowsize * samplerate /2 +1).
    """

    # samplerate, samples = wavfile.read(wav_path)
    samples, samplerate = sf.read(wav_path, dtype='int16')
    if not len(samples) > 0:
        raise ValueError('wav file is empty?')

    if bandpass and highfreq > lowfreq:
        samples = butter_bandpass_filter(data=samples, cutoff=[lowfreq, highfreq], fs=samplerate)

    signal = sigproc.preemphasis(samples, preemph)
    frames = sigproc.framesig(signal, windowsize * samplerate, stride * samplerate, winfunc=window)

    if nfft == None:
        nfft = int(windowsize * samplerate)

    pspec = sigproc.powspec(frames, nfft)
    pspec = np.where(pspec == 0, np.finfo(float).eps, pspec)

    if log_scale == True:
        feature = np.log(pspec).astype(np.float32)
    else:
        feature = pspec.astype(np.float32)
    # feature = feature.transpose()
    if normalize:
        feature = normalize_frames(feature)

    if duration:
        return feature, len(samples) / samplerate

    return feature


def Make_Fbank(filename,  # sample_rate=c.SAMPLE_RATE,
               filtertype='mel', windowsize=0.025, nfft=512, use_delta=c.USE_DELTA, use_scale=c.USE_SCALE,
               lowfreq=0, nfilt=c.FILTER_BANK, log_scale=c.USE_LOGSCALE,
               use_energy=c.USE_ENERGY, normalize=c.NORMALIZE, duration=False, multi_weight=False):

    if not os.path.exists(filename):
        raise ValueError('wav file does not exist.')

    # audio, sample_rate = sf.read(filename, dtype='float32')
    audio, sample_rate = sf.read(filename, dtype='int16')
    assert len(audio) > 0, print('wav file is empty?')

    filter_banks, energies = local_fbank(audio, samplerate=sample_rate, nfilt=nfilt, nfft=nfft, lowfreq=lowfreq,
                                         winlen=windowsize, filtertype=filtertype, winfunc=np.hamming,
                                         multi_weight=multi_weight)

    if use_energy:
        energies = energies.reshape(energies.shape[0], 1)
        filter_banks = np.concatenate((energies, filter_banks), axis=1)
        # frames_features[:, 0] = np.log(energies)

    if log_scale:
        # filter_banks = 20 * np.log10(np.maximum(filter_banks, 1e-5))
        # filter_banks = 10 * np.log10(filter_banks)
        filter_banks = np.log(filter_banks)

    if use_delta:
        delta_1 = delta(filter_banks, N=1)
        delta_2 = delta(delta_1, N=1)

        filter_banks = normalize_frames(filter_banks, Scale=use_scale)
        delta_1 = normalize_frames(delta_1, Scale=use_scale)
        delta_2 = normalize_frames(delta_2, Scale=use_scale)

        filter_banks = np.hstack([filter_banks, delta_1, delta_2])

    if normalize:
        filter_banks = normalize_frames(filter_banks, Scale=use_scale)

    frames_features = filter_banks

    if duration:
        return frames_features, len(audio) / sample_rate

    # np.save(filename.replace('.wav', '.npy'), frames_features)
    return frames_features


def Make_MFCC(filename,
              filtertype='mel', winlen=0.025, winstep=0.01,
              use_delta=c.USE_DELTA, use_scale=c.USE_SCALE,
              nfilt=c.FILTER_BANK, numcep=c.FILTER_BANK,
              use_energy=c.USE_ENERGY, lowfreq=0, nfft=512,
              normalize=c.NORMALIZE,
              duration=False):
    if not os.path.exists(filename):
        raise ValueError('wav file does not exist.')

    # sample_rate, audio = wavfile.read(filename)
    audio, sample_rate = sf.read(filename, dtype='int16')
    # audio, sample_rate = librosa.load(filename, sr=None)
    # audio = audio.flatten()
    if not len(audio) > 0:
        raise ValueError('wav file is empty?')
    feats = local_mfcc(audio, samplerate=sample_rate,
                       nfilt=nfilt, winlen=winlen,
                       winstep=winstep, numcep=numcep,
                       nfft=nfft, lowfreq=lowfreq,
                       highfreq=None, preemph=0.97,
                       ceplifter=0, appendEnergy=use_energy,
                       winfunc=np.hamming, filtertype=filtertype)

    if use_delta:
        delta_1 = delta(feats, N=1)
        delta_2 = delta(delta_1, N=1)

        filter_banks = normalize_frames(feats, Scale=use_scale)
        delta_1 = normalize_frames(delta_1, Scale=use_scale)
        delta_2 = normalize_frames(delta_2, Scale=use_scale)

        feats = np.hstack([filter_banks, delta_1, delta_2])

    if normalize:
        feats = normalize_frames(feats, Scale=use_scale)

    if duration:
        return feats, len(audio) / sample_rate

    # np.save(filename.replace('.wav', '.npy'), frames_features)
    return feats


def conver_to_wav(filename, write_path, format='m4a'):
    """
    Convert other formats into wav.
    :param filename: file path for the audio.
    :param write_path:
    :param format: formats that ffmpeg supports.
    :return: None. write the wav to local.
    """
    if not os.path.exists(filename):
        raise ValueError('File may not exist.')

    if not pathlib.Path(write_path).parent.exists():
        os.makedirs(str(pathlib.Path(write_path).parent))

    sound = AudioSegment.from_file(filename, format=format)
    sound.export(write_path, format="wav")

def read_MFB(filename):
    #audio, sr = librosa.load(filename, sr=sample_rate, mono=True)
    #audio = audio.flatten()
    try:
        audio = np.load(filename.replace('.wav', '.npy'))
    except Exception:

        raise ValueError("Load {} error!".format(filename))

    return audio


def read_Waveform(filename):
    """
    read features from npy files
    :param filename: the path of wav files.
    :return:
    """
    # audio, sr = librosa.load(filename, sr=sample_rate, mono=True)
    # audio = audio.flatten()
    audio, sample_rate = sf.read(filename, dtype='int16')

    return audio.astype(np.float32).reshape(1, -1)



def read_from_npy(filename):
    """
    read features from npy files
    :param filename: the path of wav files.
    :return:
    """
    #audio, sr = librosa.load(filename, sr=sample_rate, mono=True)
    #audio = audio.flatten()
    audio = np.load(filename.replace('.wav', '.npy'))

    return audio


class ConcateVarInput(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __init__(self, num_frames=c.NUM_FRAMES_SPECT, frame_shift=c.NUM_SHIFT_SPECT,
                 feat_type='kaldi', remove_vad=False):

        super(ConcateVarInput, self).__init__()
        self.num_frames = num_frames
        self.remove_vad = remove_vad
        self.frame_shift = frame_shift
        self.c_axis = 0 if feat_type != 'wav' else 1

    def __call__(self, frames_features):

        network_inputs = []
        output = frames_features
        while output.shape[self.c_axis] < self.num_frames:
            output = np.concatenate((output, frames_features), axis=self.c_axis)

        input_this_file = int(np.ceil(output.shape[self.c_axis] / self.frame_shift))

        for i in range(input_this_file):
            start = i * self.frame_shift

            if start < output.shape[self.c_axis] - self.num_frames:
                end = start + self.num_frames
            else:
                start = output.shape[self.c_axis] - self.num_frames
                end = output.shape[self.c_axis]
            if self.c_axis == 0:
                network_inputs.append(output[start:end])
            else:
                network_inputs.append(output[:, start:end])

        network_inputs = torch.tensor(network_inputs, dtype=torch.float32)
        if self.remove_vad:
            network_inputs = network_inputs[:, :, 1:]

        return network_inputs


class ConcateInput(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """
    def __init__(self, input_per_file=1, num_frames=c.NUM_FRAMES_SPECT, remove_vad=False):

        super(ConcateInput, self).__init__()
        self.input_per_file = input_per_file
        self.num_frames = num_frames
        self.remove_vad = remove_vad

    def __call__(self, frames_features):
        network_inputs = []

        output = frames_features
        while len(output) < self.num_frames:
            output = np.concatenate((output, frames_features), axis=0)

        for i in range(self.input_per_file):
            try:
                start = np.random.randint(low=0, high=len(output) - self.num_frames + 1)
                frames_slice = output[start:start + self.num_frames]
                network_inputs.append(frames_slice)
            except Exception as e:
                print(len(output))
                raise e

        # pdb.set_trace()
        network_inputs = np.array(network_inputs, dtype=np.float32)
        if self.remove_vad:
            network_inputs = network_inputs[:, :, 1:]

        return torch.tensor(network_inputs.squeeze())


class ConcateNumInput(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __init__(self, input_per_file=1, num_frames=c.NUM_FRAMES_SPECT, feat_type='kaldi', remove_vad=False):

        super(ConcateNumInput, self).__init__()
        self.input_per_file = input_per_file
        self.num_frames = num_frames
        self.remove_vad = remove_vad
        self.c_axis = 0 if feat_type != 'wav' else 1

    def __call__(self, frames_features):
        network_inputs = []

        output = frames_features
        while output.shape[self.c_axis] < self.num_frames:
            output = np.concatenate((output, frames_features), axis=self.c_axis)

        if len(output) / self.num_frames >= self.input_per_file:
            for i in range(self.input_per_file):
                start = i * self.num_frames
                frames_slice = output[start:start + self.num_frames] if self.c_axis == 0 else output[:,
                                                                                              start:start + self.num_frames]
                network_inputs.append(frames_slice)
        else:
            for i in range(self.input_per_file):
                try:
                    start = np.random.randint(low=0, high=output.shape[self.c_axis] - self.num_frames + 1)

                    frames_slice = output[start:start + self.num_frames] if self.c_axis == 0 else output[:,
                                                                                                  start:start + self.num_frames]
                    network_inputs.append(frames_slice)
                except Exception as e:
                    print(len(output))
                    raise e

        # pdb.set_trace()
        network_inputs = np.array(network_inputs, dtype=np.float32)
        if self.remove_vad:
            network_inputs = network_inputs[:, :, 1:]

        if len(network_inputs.shape) > 2:
            network_inputs = network_inputs.squeeze(0)
        return network_inputs


class ConcateNumInput_Test(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __init__(self, input_per_file=1, num_frames=c.NUM_FRAMES_SPECT, remove_vad=False):
        super(ConcateNumInput_Test, self).__init__()
        self.input_per_file = input_per_file
        self.num_frames = num_frames
        self.remove_vad = remove_vad

    def __call__(self, frames_features):
        network_inputs = []

        output = frames_features
        while len(output) < self.num_frames:
            output = np.concatenate((output, frames_features), axis=0)

        start = np.random.randint(low=0, high=len(output) - self.num_frames + 1)

        return start, len(output)


class concateinputfromMFB(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __init__(self, input_per_file=1, num_frames=c.NUM_FRAMES_SPECT, remove_vad=False):

        super(concateinputfromMFB, self).__init__()
        self.input_per_file = input_per_file
        self.num_frames = num_frames
        self.remove_vad = remove_vad

    def __call__(self, frames_features):
        network_inputs = []

        output = frames_features
        while len(output) < self.num_frames:
            output = np.concatenate((output, frames_features), axis=0)

        for i in range(self.input_per_file):
            try:
                start = np.random.randint(low=0, high=len(output) - self.num_frames + 1)
                frames_slice = output[start:start + self.num_frames]
                network_inputs.append(frames_slice)
            except Exception as e:
                print(len(output))
                raise e

        # pdb.set_trace()
        network_inputs = torch.tensor(network_inputs, dtype=torch.float32)
        if self.remove_vad:
            network_inputs = network_inputs[:, :, 1:]

        return network_inputs

class ConcateOrgInput(object):
    """
    prepare feats with true length.
    """

    def __init__(self, remove_vad=False):
        super(ConcateOrgInput, self).__init__()
        self.remove_vad = remove_vad

    def __call__(self, frames_features):
        # pdb.set_trace()
        network_inputs = []
        output = np.array(frames_features)

        if self.remove_vad:
            output = output[:, 1:]

        network_inputs.append(output)
        network_inputs = torch.tensor(network_inputs, dtype=torch.float32)

        return network_inputs

def pad_tensor(vec, pad, dim):
    """
    args:
        vec - tensor to pad
        pad - the size to pad to
        dim - dimension to pad
    return:
        a new tensor padded itself to 'pad' in dimension 'dim'
    """
    while vec.shape[dim]<pad:
        vec = torch.cat([vec, vec], dim=dim)

    start = np.random.randint(low=0, high=vec.shape[dim]-pad+1)
    return torch.Tensor.narrow(vec, dim=dim, start=start, length=pad)

class PadCollate:
    """
    a variant of callate_fn that pads according to the longest sequence in
    a batch of sequences
    """

    def __init__(self, dim=0, min_chunk_size=200, max_chunk_size=400, normlize=True,
                 num_batch=0, split=False, chisquare=False, noise_padding=None,
                 fix_len=False):
        """
        args:
            dim - the dimension to be padded (dimension of time in sequences)
        """
        self.dim = dim
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.num_batch = num_batch
        self.fix_len = fix_len
        self.normlize = normlize
        self.split = split
        self.chisquare = chisquare
        self.noise_padding = noise_padding

        if self.fix_len:
            self.frame_len = np.random.randint(low=self.min_chunk_size, high=self.max_chunk_size)
        else:
            assert num_batch > 0
            batch_len = np.arange(self.min_chunk_size, self.max_chunk_size + 1)

            if chisquare:
                chi_len = np.random.chisquare(min_chunk_size, 2 * (max_chunk_size - min_chunk_size)).astype(np.int32)
                batch_len = np.concatenate((chi_len, batch_len))

            print('==> Generating %d different random length...' % (len(batch_len)))

            self.batch_len = batch_len
            print('==> Average of utterance length is %d. ' % (np.mean(self.batch_len)))

    def pad_collate(self, batch):
        """
        args:
            batch - list of (tensor, label)
        reutrn:
            xs - a tensor of all examples in 'batch' after padding
            ys - a LongTensor of all labels in batch
        """
        # pdb.set_trace()
        if self.fix_len:
            frame_len = self.frame_len
        else:
            # frame_len = np.random.randint(low=self.min_chunk_size, high=self.max_chunk_size)
            frame_len = random.choice(self.batch_len)

        if self.noise_padding is not None:
            noise_features = self.noise_padding.__getrandomitem__()
            # print(noise_features.shape)
            noise_features_len = noise_features.shape[1]

            noise_len = np.random.randint(0, int(frame_len * 0.5))
            if noise_len > 0:
                if noise_len < noise_features_len:
                    start = np.random.randint(low=0, high=noise_features_len - noise_len)
                    noise_features = noise_features[:, start:(start + noise_len)]
                else:
                    noise_len = noise_features_len

                noise_features = noise_features.unsqueeze(0).repeat(len(batch), 1, 1, 1)
                frame_len -= noise_len
        else:
            noise_len = 0

        # pad according to max_len
        # print()
        xs = torch.stack(list(map(lambda x: x[0], batch)), dim=0)
        if self.split:
            xs = torch.cat(xs.chunk(2, dim=2), dim=1)
            # print(xs.shape)

        if frame_len < xs.shape[-2]:
            start = np.random.randint(low=0, high=xs.shape[-2] - frame_len)
            end = start + frame_len
            xs = xs[:, :, start:end, :].contiguous()
        else:
            # print(frame_len, xs.shape[-2])
            xs = xs.contiguous()

        if noise_len > 0:
            start = np.random.randint(low=0, high=xs.shape[-2])
            # print(noise_features.shape)
            # print(xs.shape)
            noise_features = noise_features[:, :, :, -xs.shape[-1]:]
            xs = torch.cat((xs[:, :, :start, :], noise_features, xs[:, :, start:, :]), dim=2)

        ys = torch.LongTensor(list(map(lambda x: x[1], batch)))

        # map_batch = map(lambda x_y: (pad_tensor(x_y[0], pad=frame_len, dim=self.dim - 1), x_y[1]), batch)
        # pad_batch = list(map_batch)
        #
        # xs = torch.stack(list(map(lambda x: x[0], pad_batch)), dim=0)
        # ys = torch.LongTensor(list(map(lambda x: x[1], pad_batch)))

        return xs, ys

    def __call__(self, batch):
        return self.pad_collate(batch)


class PadCollate3d:
    """
    a variant of callate_fn that pads according to the longest sequence in
    a batch of sequences
    """

    def __init__(self, dim=0, min_chunk_size=200, max_chunk_size=400, normlize=True,
                 num_batch=0,
                 fix_len=False):
        """
        args:
            dim - the dimension to be padded (dimension of time in sequences)
        """
        self.dim = dim
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.num_batch = num_batch
        self.fix_len = fix_len
        self.normlize = normlize

        if self.fix_len:
            self.frame_len = np.random.randint(low=self.min_chunk_size, high=self.max_chunk_size)
        else:
            assert num_batch > 0
            batch_len = np.arange(self.min_chunk_size, self.max_chunk_size + 1)

            print('==> Generating %d different random length...' % (len(batch_len)))
            self.batch_len = np.array(batch_len)
            print('==> Average of utterance length is %d. ' % (np.mean(self.batch_len)))

    def pad_collate(self, batch):
        """
        args:
            batch - list of (tensor, label)
        reutrn:
            xs - a tensor of all examples in 'batch' after padding
            ys - a LongTensor of all labels in batch
        """
        # pdb.set_trace()
        if self.fix_len:
            frame_len = self.frame_len
        else:
            # frame_len = np.random.randint(low=self.min_chunk_size, high=self.max_chunk_size)
            # frame_len = self.batch_len[self.iteration % self.num_batch]
            # self.iteration += 1
            # self.iteration %= self.num_batch
            # if self.iteration == 0:
            #     np.random.shuffle(self.batch_len)
            frame_len = random.choice(self.batch_len)
        # pad according to max_len
        # print()
        xs = torch.stack(list(map(lambda x: x[0], batch)), dim=0)

        if frame_len < batch[0][0].shape[-2]:
            start = np.random.randint(low=0, high=batch[0][0].shape[-2] - frame_len)
            end = start + frame_len
            xs = xs[:, :, start:end, :].contiguous()
        else:
            xs = xs.contiguous()

        ys = torch.LongTensor(list(map(lambda x: x[1], batch)))
        if isinstance(batch[0][2], torch.Tensor):
            zs = torch.stack(list(map(lambda x: x[2], batch)), dim=0)
        else:
            zs = torch.LongTensor(list(map(lambda x: x[2], batch)))

        # map_batch = map(lambda x_y: (pad_tensor(x_y[0], pad=frame_len, dim=self.dim - 1), x_y[1]), batch)
        # pad_batch = list(map_batch)
        #
        # xs = torch.stack(list(map(lambda x: x[0], pad_batch)), dim=0)
        # ys = torch.LongTensor(list(map(lambda x: x[1], pad_batch)))

        return xs, ys, zs

    def __call__(self, batch):
        return self.pad_collate(batch)


class RNNPadCollate:
    """
    a variant of callate_fn that pads according to the longest sequence in
    a batch of sequences
    """

    def __init__(self, dim=0):
        """
        args:
            dim - the dimension to be padded (dimension of time in sequences)
        """
        self.dim = dim

    def pad_collate(self, batch):
        """
        args:
            batch - list of (tensor, label)
        reutrn:
            xs - a tensor of all examples in 'batch' after padding
            ys - a LongTensor of all labels in batch
        """
        # pdb.set_trace()
        # pad according to max_len
        data = [x[0][0] for x in batch]
        data = [x[:, :40].float() for x in data]
        data_len = np.array([len(x) for x in data])
        sort_idx = np.argsort(-data_len)
        sort_data = [data[sort_idx[i]] for i in range(len(sort_idx))]

        labels = [x[1] for x in batch]
        sort_label = [labels[sort_idx[i]] for i in range(len(sort_idx))]
        # data.sort(key=lambda x: len(x), reverse=True)

        sort_label = torch.LongTensor(sort_label)

        data_length = [len(sq) for sq in sort_data]
        p_data = rnn_utils.pad_sequence(sort_data, batch_first=True, padding_value=0)
        batch_x_pack = rnn_utils.pack_padded_sequence(p_data, data_length, batch_first=True)

        return batch_x_pack, sort_label, data_length


    def __call__(self, batch):
        return self.pad_collate(batch)


class TripletPadCollate:
    """
    a variant of callate_fn that pads according to the longest sequence in
    a batch of sequences
    """

    def __init__(self, dim=0):
        """
        args:
            dim - the dimension to be padded (dimension of time in sequences)
        """
        self.dim = dim
        self.min_chunk_size = 300
        self.max_chunk_size = 500
        self.num_chunk = np.random.randint(low=self.min_chunk_size, high=self.max_chunk_size)

    def pad_collate(self, batch):
        """
        args:
            batch - list of (tensor, label)
        reutrn:
            xs - a tensor of all examples in 'batch' after padding
            ys - a LongTensor of all labels in batch
        """
        # pdb.set_trace()
        # find longest sequence

        # max_len = max(map(lambda x: x[0].shape[self.dim], batch))
        frame_len = self.num_chunk
        # pad according to max_len
        map_batch = map(lambda x_y: (pad_tensor(x_y[0], pad=frame_len, dim=self.dim),
                                     pad_tensor(x_y[1], pad=frame_len, dim=self.dim),
                                     pad_tensor(x_y[2], pad=frame_len, dim=self.dim),
                                     x_y[3],
                                     x_y[4]), batch)
        pad_batch = list(map_batch)
        # stack all

        xs_a = torch.stack(list(map(lambda x: x[0], pad_batch)), dim=0)
        xs_p = torch.stack(list(map(lambda x: x[1], pad_batch)), dim=0)
        xs_n = torch.stack(list(map(lambda x: x[2], pad_batch)), dim=0)

        ys_a = torch.LongTensor(list(map(lambda x: x[3], pad_batch)))
        ys_n = torch.LongTensor(list(map(lambda x: x[4], pad_batch)))


        return xs_a, xs_p, xs_n, ys_a, ys_n

    def __call__(self, batch):
        return self.pad_collate(batch)


class ExtractCollate:
    """
    a variant of callate_fn that pads according to the longest sequence in
    a batch of sequences
    """

    def __init__(self, dim=0):
        """
        args:
            dim - the dimension to be padded (dimension of time in sequences)
        """
        self.dim = dim
        self.min_chunk_size = 300
        self.max_chunk_size = 500
        self.num_chunk = np.random.randint(low=self.min_chunk_size, high=self.max_chunk_size)

    def extract_collate(self, batch):
        """
        args:
            batch - list of (tensor, label)
        reutrn:
            xs - a tensor of all examples in 'batch' after padding
            ys - a LongTensor of all labels in batch
        """
        # pdb.set_trace()
        # find longest sequence

        # max_len = max(map(lambda x: x[0].shape[self.dim], batch))
        frame_len = self.num_chunk
        # pad according to max_len
        map_batch = map(lambda x_y: (pad_tensor(x_y[0], pad=frame_len, dim=self.dim), x_y[1]), batch)
        pad_batch = list(map_batch)
        # stack all

        xs = torch.stack(list(map(lambda x: x[0], pad_batch)), dim=0)
        ys = torch.LongTensor(list(map(lambda x: x[1], pad_batch)))
        uid = [x[2] for x in batch]

        return xs, ys, uid

    def __call__(self, batch):
        return self.extract_collate(batch)


class truncatedinputfromSpectrogram(object):
    """truncated input from Spectrogram
    """
    def __init__(self, input_per_file=1):

        super(truncatedinputfromSpectrogram, self).__init__()
        self.input_per_file = input_per_file

    def __call__(self, frames_features):

        network_inputs = []
        frames_features = np.swapaxes(frames_features, 0, 1)
        num_frames = len(frames_features)
        import random

        for i in range(self.input_per_file):

            j=0

            if c.NUM_PREVIOUS_FRAME_SPECT <= (num_frames - c.NUM_NEXT_FRAME_SPECT):
                j = random.randrange(c.NUM_PREVIOUS_FRAME_SPECT, num_frames - c.NUM_NEXT_FRAME_SPECT)

            #j = random.randrange(c.NUM_PREVIOUS_FRAME_SPECT, num_frames - c.NUM_NEXT_FRAME_SPECT)
            # If len(frames_features)<NUM__FRAME_SPECT, then apply zero padding.
            if j==0:
                frames_slice = np.zeros((c.NUM_FRAMES_SPECT, c.NUM_FFT/2+1), dtype=np.float32)
                frames_slice[0:(frames_features.shape[0])] = frames_features
            else:
                frames_slice = frames_features[j - c.NUM_PREVIOUS_FRAME_SPECT:j + c.NUM_NEXT_FRAME_SPECT]

            network_inputs.append(frames_slice)

        return np.array(network_inputs)


def read_audio(filename, sample_rate=c.SAMPLE_RATE):
    audio, sr = librosa.load(filename, sr=sample_rate, mono=True)
    audio = audio.flatten()
    return audio

#this is not good
#def normalize_frames(m):
#    return [(v - np.mean(v)) / (np.std(v) + 2e-12) for v in m]

def normalize_frames(m, Scale=True):
    """
    Normalize frames with mean and variance
    :param m:
    :param Scale:
    :return:
    """
    if Scale:
        return (m - np.mean(m, axis=0)) / (np.std(m, axis=0) + 1e-12)

    return (m - np.mean(m, axis=0))


def pre_process_inputs(signal=np.random.uniform(size=32000), target_sample_rate=8000, use_delta=c.USE_DELTA):

    filter_banks, energies = fbank(signal, samplerate=target_sample_rate, nfilt=c.FILTER_BANK, winlen=0.025)
    delta_1 = delta(filter_banks, N=1)
    delta_2 = delta(delta_1, N=1)

    filter_banks = normalize_frames(filter_banks)
    delta_1 = normalize_frames(delta_1)
    delta_2 = normalize_frames(delta_2)

    if use_delta:
        frames_features = np.hstack([filter_banks, delta_1, delta_2])
    else:
        frames_features = filter_banks
    num_frames = len(frames_features)
    network_inputs = []
    """Too complicated
    for j in range(c.NUM_PREVIOUS_FRAME, num_frames - c.NUM_NEXT_FRAME):
        frames_slice = frames_features[j - c.NUM_PREVIOUS_FRAME:j + c.NUM_NEXT_FRAME]
        #network_inputs.append(np.reshape(frames_slice, (32, 20, 3)))
        network_inputs.append(frames_slice)
        
    """
    import random
    j = random.randrange(c.NUM_PREVIOUS_FRAME, num_frames - c.NUM_NEXT_FRAME)
    frames_slice = frames_features[j - c.NUM_PREVIOUS_FRAME:j + c.NUM_NEXT_FRAME]
    network_inputs.append(frames_slice)
    return np.array(network_inputs)


class truncatedinput(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __call__(self, input):

        #min_existing_frames = min(self.libri_batch['raw_audio'].apply(lambda x: len(x)).values)
        want_size = int(c.TRUNCATE_SOUND_FIRST_SECONDS * c.SAMPLE_RATE)
        if want_size > len(input):
            output = np.zeros((want_size,))
            output[0:len(input)] = input
            #print("biho check")
            return output
        else:
            return input[0:want_size]


class toMFB(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __call__(self, input):

        output = pre_process_inputs(input, target_sample_rate=c.SAMPLE_RATE)
        return output


class totensor(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __call__(self, input):
        """
        Args:
            pic (PIL.Image or numpy.ndarray): Image to be converted to tensor.

        Returns:
            Tensor: Converted image.
        """
        input = torch.tensor(input, dtype=torch.float32)
        return input.unsqueeze(0)


class to2tensor(object):
    """Rescales the input PIL.Image to the given 'size'.
    If 'size' is a 2-element tuple or list in the order of (width, height), it will be the exactly size to scale.
    If 'size' is a number, it will indicate the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the exactly size or the smaller edge
    interpolation: Default: PIL.Image.BILINEAR
    """

    def __call__(self, pic):
        """
        Args:
            pic (PIL.Image or numpy.ndarray): Image to be converted to tensor.

        Returns:
            Tensor: Converted image.
        """
        # if isinstance(pic, np.ndarray):
            # handle numpy array
        img = torch.tensor(pic, dtype=torch.float32)
        return img


class tonormal(object):

    def __call__(self, tensor):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.

        Returns:
            Tensor: Normalized image.
        """
        # TODO: make efficient
        tensor = tensor - torch.mean(tensor)

        return tensor.float()


class mvnormal(object):

    def __call__(self, tensor):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.

        Returns:
            Tensor: Normalized image.
        """
        # TODO: make efficient
        tensor = (tensor - torch.mean(tensor, dim=-2, keepdim=True)) / torch.std(tensor, dim=-2, keepdim=True).add_(
            1e-12)

        return tensor.float()


class tolog(object):

    def __call__(self, tensor):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.

        Returns:
            Tensor: Normalized image.
        """
        tensor = torch.log(tensor)

        return tensor.float()
