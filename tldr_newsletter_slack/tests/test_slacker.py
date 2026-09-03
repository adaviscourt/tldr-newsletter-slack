import unittest
from unittest.mock import MagicMock, patch

from tldr_newsletter_slack.slacker import Slacker, slack_icon_emoji


class SlackIconEmojiTest(unittest.TestCase):
    def test_slack_icon_emoji_converts_unicode_to_slack_shortcode(self):
        self.assertEqual(slack_icon_emoji("📊"), ":bar_chart:")
        self.assertEqual(slack_icon_emoji("📝"), ":memo:")

    def test_slack_icon_emoji_preserves_existing_shortcode(self):
        self.assertEqual(slack_icon_emoji(":robot_face:"), ":robot_face:")

    def test_post_message_sends_normalized_icon_emoji(self):
        with patch("tldr_newsletter_slack.slacker.slack_sdk.WebClient") as web_client:
            client = MagicMock()
            web_client.return_value = client

            Slacker("C123", "token").post_message("hello", "Data", "📊")

            client.chat_postMessage.assert_called_once_with(
                channel="C123",
                text="hello",
                username="Data",
                icon_emoji=":bar_chart:",
                unfurl_links=False,
            )


if __name__ == "__main__":
    unittest.main()
