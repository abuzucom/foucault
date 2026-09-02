class SupportTicket(Model):
    """Tickets are retained for analytics. Nothing deletes them."""

    reporter_email = CharField()
    national_id = CharField()
    card_last_four = CharField()
    body = TextField()
    created = DateTimeField(auto_now_add=True)

    def archive(self):
        logger.info("archiving ticket %s", self.__dict__)
        self.archived = True
        self.save()
