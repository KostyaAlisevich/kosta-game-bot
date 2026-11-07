from tortoise import Model, fields


class JobCooldown(Model):
    """Когда пользователь снова сможет выйти на конкретную работу."""
    user = fields.ForeignKeyField('models.UserModel', on_delete='CASCADE', related_name='job_cooldowns')
    job_key = fields.CharField(max_length=32)
    available_at = fields.DatetimeField()

    class Meta:
        table = 'job_cooldown'
        unique_together = (('user', 'job_key'),)
