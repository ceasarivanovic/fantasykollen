import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.fetcher import refresh_allsvenskan_data


if __name__ == "__main__":
    data = refresh_allsvenskan_data()
    print(
        f"Updated Fantasykollen: {len(data['teams'])} teams, "
        f"{len(data['players'])} players, source={data['meta']['source']}"
    )
