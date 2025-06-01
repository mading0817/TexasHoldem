"""德州扑克CLI游戏界面.

这个模块提供命令行界面的德州扑克游戏实现，使用v2控制器API。
采用分层设计，将显示逻辑和输入处理分离到专门的模块中。
"""

import logging
from typing import Optional

from v2.controller import PokerController, HandResult
from v2.core import Action, ActionType, GameSnapshot, Phase, SeatStatus, Player
from v2.ai import SimpleAI
from .render import CLIRenderer
from .input_handler import CLIInputHandler


class TexasHoldemCLI:
    """德州扑克CLI游戏界面.
    
    提供命令行界面的德州扑克游戏体验，支持人机对战。
    使用分层设计，将显示逻辑和输入处理分离到专门的模块中。
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
        
        # 创建渲染器和输入处理器
        self.renderer = CLIRenderer()
        self.input_handler = CLIInputHandler()
        
        # 初始化玩家
        self._setup_players()
        
    def _setup_players(self) -> None:
        """设置玩家.
        
        为游戏添加指定数量的玩家，包括人类玩家和AI玩家。
        """
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
                player = Player(
                    seat_id=i,
                    name=name,
                    chips=self.initial_chips
                )
                self.controller._game_state.add_player(player)
    
    def run(self) -> None:
        """运行游戏主循环.
        
        执行完整的德州扑克游戏流程，包括多手牌的连续游戏。
        """
        # 显示游戏开始信息
        header = self.renderer.render_game_header(
            0, self.num_players, self.initial_chips, self.human_seat
        )
        self.logger.info(header)
        
        hand_count = 0
        
        while True:
            hand_count += 1
            
            # 显示手牌开始信息
            hand_header = self.renderer.render_game_header(
                hand_count, self.num_players, self.initial_chips, self.human_seat
            )
            self.logger.info(f"\n{hand_header.split('===')[-1].strip()}")
            
            # 开始新手牌
            if not self.controller.start_new_hand():
                game_over_msg = self.renderer.render_game_over("活跃玩家不足")
                self.logger.info(game_over_msg)
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
        """显示当前游戏状态.
        
        使用渲染器将游戏状态快照转换为格式化的显示内容。
        """
        snapshot = self.controller.get_snapshot()
        state_display = self.renderer.render_game_state(snapshot, self.human_seat)
        self.logger.info(f"\n{state_display}")
    
    def _handle_human_action(self) -> None:
        """处理人类玩家行动.
        
        使用输入处理器获取用户输入，并通过控制器执行行动。
        """
        try:
            snapshot = self.controller.get_snapshot()
            action_input = self.input_handler.get_player_action(snapshot, self.human_seat)
            
            # 转换为Action对象
            action = Action(
                player_id=action_input.player_id,
                action_type=action_input.action_type,
                amount=action_input.amount
            )
            
            # 执行行动
            success = self.controller.execute_action(action)
            if not success:
                error_msg = self.renderer.render_error_message("行动执行失败")
                self.logger.info(error_msg)
                
        except Exception as e:
            error_msg = self.renderer.render_error_message(str(e))
            self.logger.info(error_msg)
    
    def _handle_ai_action(self, player_id: int) -> None:
        """处理AI玩家行动.
        
        Args:
            player_id: AI玩家ID
        """
        snapshot = self.controller.get_snapshot()
        player = next(p for p in snapshot.players if p.seat_id == player_id)
        
        try:
            # 让控制器处理AI行动
            success = self.controller.process_ai_action()
            
            if success:
                # 获取更新后的快照来显示AI行动
                new_snapshot = self.controller.get_snapshot()
                # 这里可以通过事件系统获取具体的行动描述
                # 暂时使用简单的显示
                ai_action_msg = self.renderer.render_ai_action(
                    player.name, "执行了行动"
                )
                self.logger.info(ai_action_msg)
            else:
                error_msg = self.renderer.render_error_message(f"{player.name} AI行动失败")
                self.logger.info(error_msg)
                
        except Exception as e:
            error_msg = self.renderer.render_error_message(f"{player.name} AI行动异常: {e}")
            self.logger.info(error_msg)
    
    def _display_hand_result(self, result: HandResult) -> None:
        """显示手牌结果.
        
        Args:
            result: 手牌结果对象
        """
        snapshot = self.controller.get_snapshot()
        result_display = self.renderer.render_hand_result(result, snapshot)
        self.logger.info(result_display)
    
    def _should_continue(self) -> bool:
        """检查是否应该继续游戏.
        
        Returns:
            True表示继续，False表示退出
        """
        # 检查是否还有足够的活跃玩家
        snapshot = self.controller.get_snapshot()
        active_players = [
            p for p in snapshot.players 
            if p.status == SeatStatus.ACTIVE and p.chips > 0
        ]
        
        if len(active_players) < 2:
            game_over_msg = self.renderer.render_game_over("只剩一个玩家有筹码")
            self.logger.info(game_over_msg)
            return False
        
        # 询问用户是否继续
        return self.input_handler.get_continue_choice()


def main():
    """CLI游戏入口函数.
    
    创建并运行德州扑克CLI游戏。
    """
    try:
        game = TexasHoldemCLI()
        game.run()
    except KeyboardInterrupt:
        print("\n游戏被用户中断")
    except Exception as e:
        print(f"游戏运行错误: {e}")


if __name__ == "__main__":
    main() 