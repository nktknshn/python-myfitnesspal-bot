
import myfitnesspal
from six.moves.urllib import parse
import lxml


class RecentFood(myfitnesspal.base.MFPBase):
    def __init__(self, id, name, qty, weights):
        self._name = name
        self._id = id
        self._qty = qty
        self._weights = weights

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @property
    def qty(self):
        return self._qty

    @property
    def weights(self):
        return self._weights

    @property
    def selected_weight(self):
        for w in self._weights:
            if w.selected:
                return w
        return None

    def __unicode__(self):
        return u'%d -- %s -- %s -- %s' % (
            self.id,
            self.name,
            self.qty,
            self.weights
        )


class RecentFoodWeight(myfitnesspal.base.MFPBase):
    def __init__(self, id, name, selected=False):
        self._id = id
        self._name = name
        self._selected = selected

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def selected(self):
        return self._selected

    def __unicode__(self):
        return u'%d -- %s -- %s' % (
            self.id,
            self.name,
            self.selected
        )


class ExtendedClient(myfitnesspal.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_url_for_recent_food(self):
        return parse.urljoin(
            self.BASE_URL_SECURE,
            'food/load_recent'
        )

    def _get_recent_food(self, document):
        pass

    def get_recent_food(self):
        document = self._get_document_for_url(
            'https://www.myfitnesspal.com/user/%s/diary/add?meal=0' % (
                self.effective_username)
        )

        rows = document.xpath("//tr[@class='favorite']")

        recent_food = []

        for row in rows:
            checkbox, name, qtys = row

            qty = float(qtys[1].get('value'))

            weights = list(map(lambda qrow: RecentFoodWeight(
                int(qrow.get('value')), qrow.text, not qrow.get('selected') is None), qtys[3]))

            recent_food.append(
                RecentFood(
                    int(checkbox[0].get('value')),
                    name.text,
                    qty,
                    weights
                )
            )

        return recent_food

    def add_food(self, date, meal, food_id, weight_id, qty):
        url = parse.urljoin(
            self.BASE_URL_SECURE,
            'food/add_favorites'
        )

        data = {}
        data['authenticity_token'] = self._authenticity_token
        data['date'] = date
        data['meal'] = meal
        data['add'] = 'Add Checked'

        data['favorites[0][food_id]'] = food_id
        data['favorites[0][checked]'] = 1
        data['favorites[0][quantity]'] = qty
        data['favorites[0][weight_id]'] = weight_id

        print(data)

        result = self.session.post(
            url,
            data=data
        )

        # throw an error if it failed.
        if not result.ok:
            raise RuntimeError(
                "Unable to add food in MyFitnessPal: "
                "status code: {status}".format(
                    status=result.status_code
                )
            )

        document = lxml.html.document_fromstring(result.content)

        return self._get_total_from_result(document)

    def _get_total_from_result(self, document):
        total = int(document.xpath(
            "//tr[@class='total']")[0][1].text.replace(',', ''))

        total_alt = int(document.xpath(
            "//tr[@class='total alt']")[0][1].text.replace(',', ''))

        total_remaining = int(document.xpath(
            "//tr[@class='total remaining']")[0][1].text.replace(',', ''))

        return total, total_alt, total_remaining


if __name__ == "__main__":
    pass