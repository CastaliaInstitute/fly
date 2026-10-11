import unittest

from research.src.fly_memory import (
    ModelParameters,
    MushroomBodyToy,
    acquisition_experiment,
    extinction_experiment,
    mean_sem,
    reversal_experiment,
)


class MushroomBodyToyTests(unittest.TestCase):
    def test_pairing_changes_only_the_trained_cue(self):
        model = MushroomBodyToy()
        self.assertEqual(model.recall("A")["value"], 0)
        model.condition("A", 1)
        self.assertGreater(model.recall("A")["value"], 0)
        self.assertEqual(model.recall("B")["value"], 0)

    def test_extinction_reduces_learned_value(self):
        model = MushroomBodyToy()
        for _ in range(6):
            model.condition("A", 1)
        before = model.recall("A")["value"]
        for _ in range(6):
            model.extinction_trial("A")
        self.assertLess(model.recall("A")["value"], before)

    def test_reproducible_patterns_and_trials(self):
        first = MushroomBodyToy(ModelParameters(seed=11))
        second = MushroomBodyToy(ModelParameters(seed=11))
        self.assertTrue((first.patterns["A"] == second.patterns["A"]).all())
        self.assertEqual(acquisition_experiment(replicates=2, trials=3), acquisition_experiment(replicates=2, trials=3))

    def test_experiments_emit_plot_ready_records(self):
        acquisition = acquisition_experiment(replicates=3, trials=4)
        extinction = extinction_experiment(replicates=3, acquisition_trials=4, extinction_trials=3)
        reversal = reversal_experiment(replicates=3, acquisition_trials=4, reversal_trials=3)
        self.assertEqual(len(acquisition), 24)
        self.assertEqual(len(extinction), 12)
        self.assertEqual(len(reversal), 21)
        summary = mean_sem(acquisition, group_by=("group", "trial"))
        self.assertTrue(all("mean" in row and "sem" in row for row in summary))


if __name__ == "__main__":
    unittest.main()
