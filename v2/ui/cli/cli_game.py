"""德州扑克CLI游戏界面.

这个模块提供命令行界面的德州扑克游戏实现，使用v2控制器API。
"""

import logging
from typing import Optional

from v2.controller import PokerController, HandResult
from v2.core import Action, ActionType, GameSnapshot, Phase, SeatStatus
from v2.ai import SimpleAI


class TexasHoldemCLI:
    """德州扑克CLI游戏界面.
    
    提供命令行界面的德州扑克游戏体验，支持人机对战。
    """
    
    def __init__(self, human_seat: int = 0, num_players: int = 4, initial_chips: int = 1000):
        """初始化CLI游戏.
        
        Args:
            human_seat: 人类玩家座位号
            num_players: 总玩家数
            initial_chips: 初始筹码数
        """
        self.human_seat = human_seat
        self.num_players = num_players
        self.initial_chips = initial_chips
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        
        # 创建控制器
        self.controller = PokerController(
            ai_strategy=SimpleAI(),
            logger=self.logger
        )
        
        # 初始化玩家
        self._setup_players()
        
    def _setup_players(self) -> None:
        """设置玩家."""
        # 添加玩家到游戏状态
        for i in range(self.num_players):
            if i == self.human_seat:
                name = "You"
            else:
                name = f"AI_{i}"
            
            # 通过控制器的游戏状态添加玩家
            snapshot = self.controller.get_snapshot()
            if len(snapshot.players) <= i:
                # 需要添加玩家
                player_data = {
                    'seat_id': i,
                    'name': name,
                    'chips': self.initial_chips,
                    'status': SeatStatus.ACTIVE
                }
                # 直接操作游戏状态（临时方案，后续应通过控制器接口）
                from v2.core import Player
                player = Player(
                    seat_id=i,
                    name=name,
                    chips=self.initial_chips
                )
                self.controller._game_state.add_player(player)
    
    def run(self) -> None:
        """运行游戏主循环."""
        self.logger.info("=== 德州扑克 v2 CLI ===")
        self.logger.info(f"玩家数: {self.num_players}, 初始筹码: {self.initial_chips}")
        self.logger.info(f"您是玩家 {self.human_seat}")
        self.logger.info("")
        
        hand_count = 0
        
        while True:
            hand_count += 1
            self.logger.info(f"\n=== 第 {hand_count} 手牌 ===")
            
            # 开始新手牌
            if not self.controller.start_new_hand():
                self.logger.info("游戏结束：活跃玩家不足")
                break
            
            # 显示初始状态
            self._display_game_state()
            
            # 游戏循环
            while not self.controller.is_hand_over():
                current_player_id = self.controller.get_current_player_id()
                
                if current_player_id is None:
                    break
                
                if current_player_id == self.human_seat:
                    # 人类玩家行动
                    self._handle_human_action()
                else:
                    # AI玩家行动
                    self._handle_ai_action(current_player_id)
                
                # 显示更新后的状态
                self._display_game_state()
            
            # 结束手牌
            result = self.controller.end_hand()
            if result:
                self._display_hand_result(result)
            
            # 检查是否继续游戏
            if not self._should_continue():
                break
        
        self.logger.info("\n感谢游戏！")
    
    def _display_game_state(self) -> None:
        """显示当前游戏状态."""
        snapshot = self.controller.get_snapshot()
        
        self.logger.info(f"\n阶段: {snapshot.phase.value}")
        self.logger.info(f"底池: {snapshot.pot}")
        self.logger.info(f"当前最高下注: {snapshot.current_bet}")
        
        # 显示公共牌
        if snapshot.community_cards:
            cards_str = " ".join([f"{card.rank.value}{card.suit.value}" 
                                for card in snapshot.community_cards])
            self.logger.info(f"公共牌: {cards_str}")
        
        # 显示玩家信息
        self.logger.info("\n玩家状态:")
        for player in snapshot.players:
            status_str = ""
            if player.status == SeatStatus.FOLDED:
                status_str = " [弃牌]"
            elif player.status == SeatStatus.ALL_IN:
                status_str = " [全押]"
            
            current_marker = " <-- 当前" if snapshot.current_player == player.seat_id else ""
            
            # 显示手牌（仅对人类玩家）
            cards_str = ""
            if player.seat_id == self.human_seat and player.hole_cards:
                cards_str = f" 手牌: {player.hole_cards[0].rank.value}{player.hole_cards[0].suit.value} " \
                           f"{player.hole_cards[1].rank.value}{player.hole_cards[1].suit.value}"
            
            self.logger.info(f"  {player.name}: 筹码={player.chips}, 当前下注={player.current_bet}{status_str}{current_marker}{cards_str}")
    
    def _handle_human_action(self) -> None:
        """处理人类玩家行动."""
        snapshot = self.controller.get_snapshot()
        current_player = next(p for p in snapshot.players if p.seat_id == self.human_seat)
        
        self.logger.info(f"\n轮到您行动 (筹码: {current_player.chips})")
        
        # 获取可用行动
        available_actions = self._get_available_actions(current_player, snapshot)
        
        # 显示选项
        self.logger.info("可用行动:")
        for i, (action_type, description, amount) in enumerate(available_actions):
            self.logger.info(f"  {i + 1}. {description}")
        
        # 获取用户选择
        while True:
            try:
                choice = input("请选择行动 (输入数字): ").strip()
                if not choice:
                    continue
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(available_actions):
                    action_type, _, amount = available_actions[choice_idx]
                    
                    # 如果是加注，需要输入金额
                    if action_type in [ActionType.BET, ActionType.RAISE]:
                        amount = self._get_bet_amount(action_type, snapshot)
                    
                    # 创建并执行行动
                    action = Action(
                        player_id=self.human_seat,
                        action_type=action_type,
                        amount=amount
                    )
                    
                    self.controller.execute_action(action)
                    break
                else:
                    self.logger.info("无效选择，请重新输入")
            except (ValueError, KeyboardInterrupt):
                self.logger.info("无效输入，请重新输入")
            except Exception as e:
                self.logger.info(f"行动失败: {e}")
    
    def _get_available_actions(self, player, snapshot) -> list:
        """获取可用行动列表."""
        actions = []
        
        # 弃牌
        actions.append((ActionType.FOLD, "弃牌", 0))
        
        # 跟注或过牌
        call_amount = snapshot.current_bet - player.current_bet
        if call_amount == 0:
            actions.append((ActionType.CHECK, "过牌", 0))
        else:
            if call_amount <= player.chips:
                actions.append((ActionType.CALL, f"跟注 ({call_amount})", call_amount))
        
        # 下注或加注
        if snapshot.current_bet == 0:
            # 下注
            if player.chips > 0:
                actions.append((ActionType.BET, "下注", 0))
        else:
            # 加注
            min_raise = snapshot.current_bet * 2 - player.current_bet
            if min_raise <= player.chips:
                actions.append((ActionType.RAISE, "加注", 0))
        
        # 全押
        if player.chips > 0:
            actions.append((ActionType.ALL_IN, f"全押 ({player.chips})", player.chips))
        
        return actions
    
    def _get_bet_amount(self, action_type: ActionType, snapshot: GameSnapshot) -> int:
        """获取下注金额."""
        current_player = next(p for p in snapshot.players if p.seat_id == self.human_seat)
        
        if action_type == ActionType.BET:
            min_bet = 10  # 最小下注
            max_bet = current_player.chips
            prompt = f"请输入下注金额 ({min_bet}-{max_bet}): "
        else:  # RAISE
            min_raise = snapshot.current_bet * 2 - current_player.current_bet
            max_raise = current_player.chips
            prompt = f"请输入加注总额 ({min_raise}-{max_raise}): "
        
        while True:
            try:
                amount_str = input(prompt).strip()
                if not amount_str:
                    continue
                
                amount = int(amount_str)
                
                if action_type == ActionType.BET:
                    if min_bet <= amount <= max_bet:
                        return amount
                else:  # RAISE
                    if min_raise <= amount <= max_raise:
                        return amount
                
                self.logger.info("金额超出范围，请重新输入")
            except (ValueError, KeyboardInterrupt):
                self.logger.info("无效输入，请重新输入")
    
    def _handle_ai_action(self, player_id: int) -> None:
        """处理AI玩家行动."""
        snapshot = self.controller.get_snapshot()
        ai_player = next(p for p in snapshot.players if p.seat_id == player_id)
        
        self.logger.info(f"\n{ai_player.name} 正在思考...")
        
        # 让控制器处理AI行动
        if self.controller.process_ai_action():
            # 获取更新后的快照来显示AI的行动
            new_snapshot = self.controller.get_snapshot()
            # 这里可以通过事件系统获取AI的具体行动，暂时简化处理
            self.logger.info(f"{ai_player.name} 完成行动")
        else:
            self.logger.info(f"{ai_player.name} 行动失败")
    
    def _display_hand_result(self, result: HandResult) -> None:
        """显示手牌结果."""
        self.logger.info(f"\n=== 手牌结束 ===")
        self.logger.info(f"底池: {result.pot_amount}")
        
        if result.winner_ids:
            winner_names = []
            snapshot = self.controller.get_snapshot()
            for winner_id in result.winner_ids:
                winner = next(p for p in snapshot.players if p.seat_id == winner_id)
                winner_names.append(winner.name)
            
            self.logger.info(f"获胜者: {', '.join(winner_names)}")
            if result.winning_hand_description:
                self.logger.info(f"获胜牌型: {result.winning_hand_description}")
        else:
            self.logger.info("无获胜者")
    
    def _should_continue(self) -> bool:
        """检查是否继续游戏."""
        snapshot = self.controller.get_snapshot()
        
        # 检查活跃玩家数
        active_players = [p for p in snapshot.players 
                         if p.status == SeatStatus.ACTIVE and p.chips > 0]
        
        if len(active_players) < 2:
            self.logger.info("活跃玩家不足，游戏结束")
            return False
        
        # 询问是否继续
        while True:
            try:
                choice = input("\n是否继续下一手牌？(y/n): ").strip().lower()
                if choice in ['y', 'yes', '是']:
                    return True
                elif choice in ['n', 'no', '否']:
                    return False
                else:
                    self.logger.info("请输入 y 或 n")
            except KeyboardInterrupt:
                return False


def main():
    """CLI游戏主入口."""
    try:
        game = TexasHoldemCLI()
        game.run()
    except KeyboardInterrupt:
        print("\n游戏被中断")
    except Exception as e:
        print(f"游戏出错: {e}")


if __name__ == "__main__":
    main() 