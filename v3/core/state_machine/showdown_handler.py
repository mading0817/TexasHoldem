"""
摊牌阶段处理器
"""
import logging
from typing import Dict, Any, List
from .types import GamePhase, GameEvent, GameContext
from .base_phase_handler import BasePhaseHandler
from ..pot.pot_manager import PotManager
from ..chips.chip_ledger import ChipLedger
from ..eval.evaluator import HandEvaluator
from ..eval.types import HandResult

__all__ = ['ShowdownHandler']

class ShowdownHandler(BasePhaseHandler):
    """摊牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.SHOWDOWN)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入摊牌阶段"""
        super().on_enter(ctx)
        self._determine_winners_and_distribute_pot(ctx)

    def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool:
        """摊牌后只能进入FINISHED阶段"""
        return target_phase == GamePhase.FINISHED

    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """摊牌阶段不处理玩家行动"""
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": "摊牌阶段不能执行玩家行动"},
            source_phase=self.phase
        )

    def _determine_winners_and_distribute_pot(self, ctx: GameContext) -> None:
        """
        使用PotManager和ChipLedger决定获胜者并分配底池。
        这个版本通过ChipLedger.settle_hand保证筹码结算的原子性。
        """
        logger = logging.getLogger(__name__)
        logger.info("[游戏流程] 进入摊牌阶段，开始计算胜者和分配底池...")

        showdown_players_data = {
            p_id: p_data for p_id, p_data in ctx.players.items()
            if p_data.get('status') not in ['folded', 'out']
        }
        
        if not showdown_players_data:
            logger.warning("摊牌时没有任何玩家在手，直接进入下一手。")
            # 这种情况通常由FinishedHandler处理，但作为保险
            ctx.chip_ledger.settle_hand({}) # 传入空交易以清算冻结筹码
            ctx.pot_total = 0
            return

        if len(showdown_players_data) == 1:
            winner_id = list(showdown_players_data.keys())[0]
            logger.info(f"玩家 {winner_id} 是唯一未盖牌的玩家，直接获胜。")
            
            # 即使只有一个赢家，也使用标准结算流程来确保所有筹码（包括他自己的赌注）都被正确处理
            total_pot = sum(ctx.current_hand_bets.values())
            transactions = {p: -b for p, b in ctx.current_hand_bets.items()}
            transactions[winner_id] = transactions.get(winner_id, 0) + total_pot
            
            ctx.chip_ledger.settle_hand(transactions)
            
            ctx.winners_this_hand = [{
                'player_id': winner_id,
                'amount': total_pot,
                'hand_rank': 'N/A (uncontested)',
            }]
            ctx.pot_total = 0
            logger.info(f"[游戏流程] 摊牌结算完成。玩家 {winner_id} 赢得 {total_pot}。")
            return

        # 多个玩家摊牌
        player_hand_results: Dict[str, HandResult] = {}
        for p_id, p_data in showdown_players_data.items():
            hole_cards = p_data.get('hole_cards', [])
            if not hole_cards:
                 logger.error(f"玩家 {p_id} 参与摊牌但没有手牌！这是一个严重错误。")
                 hand_strength = -1
                 hand_rank_str = "Error: No cards"
            else:
                hand_strength, hand_rank_str = HandEvaluator.evaluate_hand(hole_cards, ctx.community_cards)
            
            p_data['hand_rank_str'] = hand_rank_str
            logger.info(f"[手牌评估] 玩家 {p_id} 的手牌: {p_data['hole_cards']}, 公共牌: {ctx.community_cards}, 牌力: {hand_rank_str}")
            
            player_hand_results[p_id] = HandResult(
                player_id=p_id, 
                hand_strength=hand_strength, 
                hand_rank_str=hand_rank_str, 
                kickers=[] # 注意：当前HandEvaluator未实现Kickers
            )

        # 使用PotManager和ChipLedger进行结算
        pot_manager = PotManager(ctx.chip_ledger)
        
        side_pots = pot_manager.calculate_side_pots(ctx.current_hand_bets)
        pots_str = ", ".join([f'{sp.pot_id}({sp.amount})' for sp in side_pots])
        logger.info(f"计算出的边池结构: [{pots_str}]")

        winnings = pot_manager.distribute_pots(side_pots, player_hand_results)
        logger.info(f"底池分配结果: {winnings}")

        # 构建最终的结算交易
        transactions = {p_id: -bet for p_id, bet in ctx.current_hand_bets.items()}
        for p_id, amount in winnings.items():
            transactions[p_id] = transactions.get(p_id, 0) + amount
        
        logger.info(f"准备执行的筹码结算交易: {transactions}")
        ctx.chip_ledger.settle_hand(transactions)
        
        ctx.winners_this_hand = []
        if winnings:
            for p_id, amount in winnings.items():
                ctx.winners_this_hand.append({
                    'player_id': p_id,
                    'amount': amount,
                    'hand_rank': player_hand_results[p_id].hand_rank_str,
                })
        
        # 验证筹码守恒 (可选的调试步骤)
        final_total_chips = ctx.chip_ledger.get_total_chips()
        initial_total_chips = sum(ctx.chip_ledger.create_snapshot().player_balances.values()) # 这是一个近似值，因为快照是动态的
        logger.debug(f"手牌结算后总筹码: {final_total_chips} (近似初始值: {initial_total_chips})")


        ctx.pot_total = 0
        logger.info("[游戏流程] 摊牌阶段结束，底池分配和筹码结算完成。") 