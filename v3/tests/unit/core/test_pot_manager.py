"""
Unit tests for the PotManager class in the core pot module.
"""
import pytest
from unittest.mock import MagicMock

from v3.core.pot.pot_manager import PotManager, SidePot
from v3.core.chips.chip_ledger import ChipLedger
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestPotManager:
    """Tests for the PotManager class."""

    def setup_method(self):
        """Set up a new PotManager for each test."""
        self.chip_ledger = MagicMock(spec=ChipLedger)
        self.pot_manager = PotManager(self.chip_ledger)
        CoreUsageChecker.verify_real_objects(self.pot_manager, "PotManager")

    def test_distribute_pot_with_remainder(self):
        """
        Tests that when a pot is split, the remainder is distributed correctly.
        """
        # 1. Setup
        # Create a side pot of 100 chips to be split among 3 players
        side_pot = SidePot(pot_id="pot_0", amount=100, eligible_players={'player1', 'player2', 'player3'})
        self.pot_manager._side_pots = [side_pot]

        # Define winners, all with the same hand strength
        winners = {
            'player1': 1000,
            'player2': 1000,
            'player3': 1000,
        }
        hand_strengths = winners

        # 2. Execute
        result = self.pot_manager.distribute_winnings(winners, hand_strengths)

        # 3. Assert
        # The total distributed amount should be 100
        assert result.total_distributed == 100
        
        # The sum of individual distributions should be 100
        distributed_sum = sum(result.distributions.values())
        assert distributed_sum == 100, f"Sum of distributions was {distributed_sum}, expected 100"

        # The distribution should be 34, 33, 33 (or similar, depending on player order)
        assert sorted(result.distributions.values()) == [33, 33, 34]

        # Verify that the chip ledger was called correctly
        # The order of calls is not guaranteed due to dict iteration, so use assert_any_call
        from unittest.mock import ANY
        self.chip_ledger.add_chips.assert_any_call('player1', 34, ANY)
        self.chip_ledger.add_chips.assert_any_call('player2', 33, ANY)
        self.chip_ledger.add_chips.assert_any_call('player3', 33, ANY)

    def test_side_pot_awarded_correctly_when_main_pot_winner_is_not_eligible(self):
        """
        Tests that a side pot is awarded to the correct player even if the
        winner of the main pot is not eligible for the side pot.
        """
        # 1. Setup
        # Main pot (300 chips), eligible: A, B, C
        main_pot = SidePot(pot_id="main", amount=300, eligible_players={'A', 'B', 'C'}, is_main_pot=True)
        # Side pot (400 chips), eligible: B, C
        side_pot = SidePot(pot_id="side1", amount=400, eligible_players={'B', 'C'})
        self.pot_manager._side_pots = [main_pot, side_pot]

        # Define winners: A > C > B. Note that the 'winners' dict passed to the method
        # should only contain players who are still in the hand at showdown.
        winners_at_showdown = {
            'A': 3000,  # Best hand
            'C': 2000,  # Second best hand
            'B': 1000,  # Worst hand
        }
        hand_strengths = winners_at_showdown

        # 2. Execute
        result = self.pot_manager.distribute_winnings(winners_at_showdown, hand_strengths)

        # 3. Assert
        # Total distributed should be the sum of all pots
        assert result.total_distributed == 700
        assert sum(result.distributions.values()) == 700

        # Check the final distribution
        final_distribution = result.distributions
        assert final_distribution.get('A') == 300  # Wins main pot
        assert final_distribution.get('C') == 400  # Wins side pot
        assert final_distribution.get('B') is None # Wins nothing

        # Verify chip ledger calls
        from unittest.mock import ANY
        self.chip_ledger.add_chips.assert_any_call('A', 300, ANY)
        self.chip_ledger.add_chips.assert_any_call('C', 400, ANY)
        # Ensure B was not awarded chips
        b_was_called = any(call_args[0][0] == 'B' for call_args in self.chip_ledger.add_chips.call_args_list)
        assert not b_was_called, "Player B should not have been awarded any chips" 