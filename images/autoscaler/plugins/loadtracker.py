from datetime import datetime, timedelta


def fromisoformat(usage_time):
    return datetime.fromisoformat(usage_time[:usage_time.find('.') + 4])  # Only four decimal places


class LoadTracker:
    def __init__(self, config):
        self.overloaded = {}
        self.underloaded = {}
        self.grace = {}
        self.config = config.scaling
        self.threshold = config.scaling.wait_seconds / config.update_seconds

    def process_usage(self, container, usage):
        if container in self.grace:
            # If grace period is exceeded by measurements, remove container from grace
            if self.grace[container] < fromisoformat(usage['time']):
                del self.grace[container]
            # Otherwise, do not process usage
            else:
                return 0

        # If container is over immediate scale threshold, scale and add to grace
        if max(usage['cpu'], usage['memory']) > self.config.max_load_nowait:
            if container in self.overloaded:
                del self.overloaded[container]
                self.grace[container] = fromisoformat(usage['time']) + \
                    timedelta(seconds=self.config.grace_period)
            return 1

        # Check if scaling or descaling is needed (only one can be True)
        over, self.overloaded = self._load_check(
            self.overloaded,
            lambda u: u > self.config.max_load,
            container, usage
        )
        under, self.underloaded = self._load_check(
            self.underloaded,
            lambda u: u < self.config.min_load,
            container, usage
        )

        if over:
            return 1  # Container overloaded
        if under:
            return -1  # Container underloaded
        return 0  # Normal

    def _load_check(self, load_object, criteria, container, usage):
        # If usage means exceptional load...
        if criteria(max(usage['cpu'], usage['memory'])):
            # If not in object, add
            if container not in load_object:
                load_object[container] = LoadTracker._new_load_object(usage['time'])

            # If it is in object and time > wait_seconds, scale and add to grace
            elif fromisoformat(usage['time']) > \
                    load_object[container]['start_time'] + timedelta(seconds=self.config.wait_seconds):
                del load_object[container]
                self.grace[container] = fromisoformat(usage['time']) + \
                    timedelta(seconds=self.config.grace_period)
                return True, load_object

        # If usage means no exceptional load, but container is in object, increment normal load counter
        elif container in load_object:
            load_object[container]['normal_load_count'] += 1
            # If tolerance is reached, remove from overloaded
            if load_object[container]['normal_load_count'] >= self.config.tolerance:
                del load_object[container]

        return False, load_object  # Catch-all for non-scaling cases

    @staticmethod
    def _new_load_object(time):
        return {
            'start_time': fromisoformat(time),
            'normal_load_count': 0
        }
