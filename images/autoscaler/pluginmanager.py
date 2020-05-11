from plugins import *


class PluginManager:

    plugins = {  # Change plugins here
        1: LoadTracker
    }

    def __init__(self, config):
        if sum(PluginManager.plugins.keys()) != 1:
            raise AttributeError("Weights must add to one")
        self.plugins = {}
        for weight, plugin in PluginManager.plugins.items():
            self.plugins[weight] = plugin(config)
        self.over_threshold = config.over_threshold
        self.under_threshold = config.under_threshold

    def calculate_load(self, container, load_obj):
        result = 0
        for weight, plugin in self.plugins.items():
            result += weight * plugin.process_usage(container, load_obj)

        if result > self.over_threshold:
            return 1
        elif result < -self.under_threshold:
            return -1
        return 0

