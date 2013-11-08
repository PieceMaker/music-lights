#!/bin/env python
from __future__ import print_function
import atexit
from ConfigParserDefault import ConfigParserDefault
from itertools import cycle
from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys

import pygame.mixer
import pygame.locals

import ansi

import mainLoop
from sampleGen import SampleGen


DONE_PLAYING_CHUNK = pygame.locals.USEREVENT

STOP = 0
CONTINUE = 1


gcp = ConfigParserDefault()
gcp.read('config.ini')

useGPIO = gcp.get_def('main', 'useGPIO', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')
lightProcessNice = int(gcp.get_def('main', 'lightProcessNice', 0))
soundProcessNice = int(gcp.get_def('main', 'soundProcessNice', 0))

files = sys.argv[1:]


if soundProcessNice:
    os.nice(soundProcessNice)


class SpectrumLightController(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        sampleGen.onSample.add(self._onSample)
        sampleGen.onSongChanged.add(self._onSongChanged)

        atexit.register(self._onExit)

        if useGPIO:
            import lights_gpio as lights
        else:
            import lights

        self.messageQueue = Queue()

        self.subProcess = Process(target=lights.runLightsProcess, args=(self.messageQueue, ))
        self.subProcess.start()

    def _onSongChanged(self, tags, songInfo):
        try:
            self.messageQueue.put_nowait(('songChange', self.sampleGen.currentFilename, songInfo))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onSample(self, data):
        try:
            if isinstance(data, buffer):
                data = bytes(data)
            self.messageQueue.put_nowait(('chunk', data))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onExit(self):
        if self.subProcess.is_alive():
            try:
                self.messageQueue.put(('end', ))
            except QueueFull:
                ansi.error("Message queue to light process full! Continuing...")


class SampleOutput(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        self.channel = pygame.mixer.Channel(0)
        self.channel.set_endevent(DONE_PLAYING_CHUNK)

        self.queueNextSound()  # Start playing the first chunk.
        self.queueNextSound()  # Queue the next chunk.

        mainLoop.currentProcess.eventHandlers[DONE_PLAYING_CHUNK] = self.queueNextSound

    def queueNextSound(self, event=None):
        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=self.sampleGen,
                suppressNewline=True
                )

        chunk = pygame.mixer.Sound(buffer(self.sampleGen.nextChunk()))

        chunk.play()


def displayFileStarted(sampleGen):
    print()
    ansi.stdout(
            "Playing audio file: {style.fg.blue}{file.currentFilename}{style.none}\n"
                "{style.bold.fg.black}channels:{style.none} {file.channels}"
                "   {style.bold.fg.black}sample rate:{style.none} {file.samplerate} Hz"
                "   {style.bold.fg.black}duration:{style.none} {file.duration} s",
            file=sampleGen
            )


def runPlayerProcess(playerQueue, controllerQueue, nice=None):
    process = mainLoop.PyGameProcess(controllerQueue)

    sampleGen = SampleGen(cycle(files), gcp)
    sampleGen.onSongChanged.add(lambda *a: displayFileStarted(sampleGen))

    SampleOutput(sampleGen)
    SpectrumLightController(sampleGen)

    process.loop()


if __name__ == '__main__':
    runPlayerProcess(Queue(), Queue())
