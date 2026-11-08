import unittest

from client.conversations import ConversationStore, GROUP


def people(*pairs):
    return [{"client_id": cid, "username": name} for cid, name in pairs]


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = ConversationStore()
        self.store.set_viewer("me")
        self.store.update_participants(people(("me", "Me"), ("bob", "Bob"), ("cy", "Cy")))

    def test_default_conversation_is_group(self):
        self.assertEqual(self.store.active, GROUP)
        self.assertFalse(self.store.is_private())

    def test_peers_exclude_self_and_track_presence(self):
        self.assertNotIn("me", self.store.peers)
        self.assertTrue(self.store.peer_online("bob"))
        gone = self.store.update_participants(people(("me", "Me"), ("cy", "Cy")))
        self.assertEqual(gone, ["bob"])
        self.assertFalse(self.store.peer_online("bob"))
        self.assertEqual(self.store.peer_name("bob"), "Bob")

    def test_private_histories_are_separate_per_peer(self):
        self.store.add_private_message("bob", "Bob", "me", "Me", "hi from bob", 1)
        self.store.add_private_message("me", "Me", "bob", "Bob", "hi bob", 2)
        self.store.add_private_message("cy", "Cy", "me", "Me", "hi from cy", 3)
        self.assertEqual([m["text"] for m in self.store.messages("bob")], ["hi from bob", "hi bob"])
        self.assertEqual([m["text"] for m in self.store.messages("cy")], ["hi from cy"])
        self.assertEqual(self.store.messages(GROUP), [])

    def test_own_flag_and_storage_key_for_outgoing_messages(self):
        peer, entry = self.store.add_private_message("me", "Me", "bob", "Bob", "yo", 1)
        self.assertEqual(peer, "bob")
        self.assertTrue(entry["own"])
        peer, entry = self.store.add_private_message("bob", "Bob", "me", "Me", "hey", 2)
        self.assertEqual(peer, "bob")
        self.assertFalse(entry["own"])

    def test_unread_counts_only_for_closed_conversations_and_incoming(self):
        self.store.add_private_message("bob", "Bob", "me", "Me", "1", 1)
        self.store.add_private_message("bob", "Bob", "me", "Me", "2", 2)
        self.store.add_private_message("me", "Me", "bob", "Bob", "mine", 3)
        self.assertEqual(self.store.unread_count("bob"), 2)
        self.assertEqual(self.store.private_unread_total(), 2)
        self.store.open("bob")
        self.assertEqual(self.store.unread_count("bob"), 0)
        self.store.add_private_message("bob", "Bob", "me", "Me", "3", 4)  # open: read
        self.assertEqual(self.store.unread_count("bob"), 0)

    def test_group_stays_available_and_tracks_its_own_unread(self):
        self.store.open("bob")
        self.store.add_group_message("cy", "Cy", "group msg while in private", 1)
        self.assertEqual(self.store.unread_count(GROUP), 1)
        self.store.open(GROUP)
        self.assertEqual(self.store.unread_count(GROUP), 0)
        self.assertEqual(len(self.store.messages(GROUP)), 1)

    def test_notices_never_count_as_unread(self):
        self.store.add_notice(GROUP, "Bob joined")
        self.store.add_notice("bob", "Bob left")
        self.assertEqual(sum(self.store.unread.values()), 0)

    def test_new_session_marks_everyone_offline_until_participant_list(self):
        self.store.set_viewer("me2")
        self.assertFalse(self.store.peer_online("bob"))
        self.store.update_participants(people(("me2", "Me"), ("bob", "Bob")))
        self.assertTrue(self.store.peer_online("bob"))

    def test_offline_entries_only_when_unread_or_open(self):
        self.store.add_private_message("bob", "Bob", "me", "Me", "unread", 1)
        self.store.update_participants(people(("me", "Me"), ("cy", "Cy")))
        self.assertEqual(self.store.offline_entries(), [("bob", "Bob")])
        self.store.open("bob")
        self.assertEqual(self.store.offline_entries(), [("bob", "Bob")])  # still open
        self.store.open(GROUP)
        self.assertEqual(self.store.offline_entries(), [])

    def test_history_is_capped(self):
        for index in range(ConversationStore.MAX_HISTORY + 25):
            self.store.add_group_message("bob", "Bob", str(index), index)
        messages = self.store.messages(GROUP)
        self.assertEqual(len(messages), ConversationStore.MAX_HISTORY)
        self.assertEqual(messages[-1]["text"], str(ConversationStore.MAX_HISTORY + 24))


if __name__ == "__main__":
    unittest.main()
