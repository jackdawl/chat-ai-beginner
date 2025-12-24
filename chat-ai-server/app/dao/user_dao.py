"""用户信息相关操作"""

from typing import Optional
from app.models.user_model import UserInDB, User

"""
模拟用户数据库，这里使用字典来模拟数据库存储，包含一个默认管理员账户
"""
fake_users_db = {
    "root": {
        "username": "root",
        "full_name": "Administrator",
        "email": "root@163.com",
        # 这是"root123"的bcrypt哈希值
        "hashed_password": "$2b$12$jiHSlVYQc72WrfBlB2/vX.70MMYdWpKCkdsKoEajvwMv5x9sHzwdq",
        "disabled": False,
    }
}


class UserDAO:
    """用户模型与数据库连接层"""
    def __init__(self):
        self.db = fake_users_db


    def get_user(self, username: str) -> Optional[UserInDB]:
        """
        从数据库中获取用户信息
    
        Args:
            username (str): 用户名
    
        Returns:
            Optional[UserInDB]: 用户信息对象，如果用户不存在则返回None
        """
        if username in self.db:
            user_dict = self.db[username]
            return UserInDB(**user_dict)
        return None

    def update_user(self, user: User) -> Optional[UserInDB]:
        """
        更新数据库中用户信息

        Args:
            user: 用户更新信息

        Returns:
            Optional[UserInDB]: 返回更新后的用户信息
        """
        current_user = self.get_user(user.username)
        if user.email is not None:
            current_user.username = user.email
        if user.full_name is not None:
            current_user.full_name = user.full_name
        # 更新到DB
        self.db[current_user.username] = UserInDB.model_dump(current_user)
        return current_user

    def save_user(self, user: UserInDB) -> Optional[UserInDB]:
        """
        更新数据库中用户信息
        Args:
            user: 用户更新信息

        Returns:
            Optional[UserInDB]: 返回更新后的用户信息
        """
        user_dict = UserInDB.model_dump(user)
        # 插入到DB
        self.db[user.username] = user_dict
        return user

    def delete_user(self, username: str) -> Optional[UserInDB]:
        """
        删除数据库中用户信息
        软删除：disabled=True
        Args:
            username (str): 用户名

        Returns:
            Optional[UserInDB]: 返回删除后的用户信息
        """
        current_user = self.get_user(username)
        current_user.disabled = True
        # 更新到DB
        self.db[current_user.username] = UserInDB.model_dump(current_user)
        return current_user

    def list_user(self) -> Optional[dict]:
        """
        查询数据库中所有用户信息

        Returns:
            Optional[dict]: 返回所有用户信息
        """

        return self.db