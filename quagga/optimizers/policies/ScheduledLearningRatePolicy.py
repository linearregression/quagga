class ScheduledLearningRatePolicy(object):
    def __init__(self, schedule, logger):
        self.schedule = schedule
        self.logger = logger
        self.iteration = 0
        self.learning_rate = None

    def notify(self):
        if self.iteration in self.schedule:
            self.learning_rate = self.schedule[self.iteration]
            self.logger.info('learning rate: {}'.format(self.learning_rate))
        self.iteration += 1