from envolved import EnvVar, env_var

env_name_ev: EnvVar[str] = env_var("EnvironmentName", type=str)
metric_send_every_override_ev = env_var("METRIC_SEND_EVERY_OVERRIDE", default=25, type=int)
writes_per_second_ev = env_var("writes_per_second", default=10, type=int)
connection_string_ev = env_var("AZURE_STORAGE_CONNECTION_STRING", default="", type=str)
