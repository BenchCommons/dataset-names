"""Names Commons Dataset: primeiros nomes e sobrenomes a partir de fontes oficiais e do Wikidata."""

from importlib.metadata import version

from datasettool.sources.cache import make_user_agent

REPOSITORIO = "https://github.com/BenchCommons/dataset-names"
# Enviado em todo download (spec 007, R3.3), para os operadores das fontes saberem quem baixa.
USER_AGENT = make_user_agent("namescommons", version("names-commons-dataset"), REPOSITORIO)
