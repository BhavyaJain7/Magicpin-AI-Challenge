import json
import sys
from app.models.contexts import CategoryPayload, MerchantPayload

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# 1. Load dentists category
with open("dataset/categories/dentists.json", "r", encoding="utf-8") as f:
    cat = CategoryPayload.model_validate(json.load(f))
print(f"Loaded category: {cat.slug} with {len(cat.offer_catalog)} offers")
print(f"Taboo vocabulary: {cat.voice.vocab_taboo}")
print(f"Top digest paper: {cat.digest[0].title}")

# 2. Load Dr. Meera's clinic
with open("dataset/merchants_seed.json", "r", encoding="utf-8") as f:
    mx_data = json.load(f)["merchants"][0]
merchant = MerchantPayload.model_validate(mx_data)
print(f"Loaded merchant: {merchant.identity.name} in {merchant.identity.locality}")
print(f"Active offers: {[o.title for o in merchant.offers if o.status == 'active']}")
