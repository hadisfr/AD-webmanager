import ldap
from operator import itemgetter
from urllib import parse
from flask import abort, flash, g, redirect, render_template, request
from flask_wtf import FlaskForm
from libs.common import get_objclass
from libs.common import iri_for as url_for
from libs.common import namefrom_dn
from libs.ldap_func import (ldap_auth, ldap_delete_entry, ldap_get_entries,
                            ldap_get_group, ldap_get_user,
                            ldap_in_group, ldap_obj_has_children,
                            ldap_update_attribute)
from settings import Settings
from wtforms import SelectField, StringField, SubmitField


class FilterTreeView(FlaskForm):
    filter_str = StringField()
    filter_field = SelectField(choices=Settings.SEARCH_ATTRS)
    search = SubmitField('Search')


class BatchDelete(FlaskForm):
    delete = SubmitField('Delete Selection')


class BatchPaste(FlaskForm):
    paste = SubmitField('Paste Selection')


class BatchMoveToRoot(FlaskForm):
    toRoot = SubmitField("Move To Root")


class BatchMoveOneLevelUp(FlaskForm):
    up_aLevel = SubmitField("Move One Level Up")


def init(app):
    @app.route('/tree', methods=['GET', 'POST'])
    @app.route('/tree/<base>', methods=['GET', 'POST'])
    @ldap_auth("Domain Users")
    def tree_base(base=None):
        if not base:
            base = g.ldap['dn']
        elif not base.lower().endswith(g.ldap['dn'].lower()):
            base += ",%s" % g.ldap['dn']

        admin = ldap_in_group(Settings.ADMIN_GROUP)

        parent = None
        base_split = base.split(',')
        if not base_split[0].lower().startswith("dc"):
            parent = ",".join(base_split[1:])

        if not admin:
            abort(401)
        else:
            entry_fields = [('name', "Name")]
            
            if Settings.TREE_ATTRS:
                for item in Settings.TREE_ATTRS:
                    entry_fields.append((item[0], item[1])) 

            form = FilterTreeView(request.form)
            batch_delete = BatchDelete()
            paste = BatchPaste()
            moveToRoot = BatchMoveToRoot()
            moveOneLevelUp = BatchMoveOneLevelUp()

            if form.search.data and form.validate():
                filter_str = form.filter_str.data
                filter_field = form.filter_field.data
                scope = "subtree"
                entries = get_entries(filter_str, filter_field, base, scope)
                print('1', entries)    
            else:
                filter_str = None
                scope = "onelevel"
                entries = get_entries("top", "objectClass", base, scope)
            # TODO: batch delete confirmation page
            # batch delete
            if batch_delete.delete.data:
                checkedData = request.form.getlist("checkedItems")  # returns an array of Strings, tho the strings have dict format
                toDelete = translation(checkedData)
                try:
                    deleted_list = delete_batch(toDelete)
                    flash_amount(deleted_list, deleted=True)
                except ldap.LDAPError as e:
                    flash(e, "error")
                return redirect(url_for('tree_base', base=base))
            # batch move (1 in)
            elif paste.paste.data:
                checkedData = request.form.getlist("checkedItems")
                moveTo = request.form.get("moveHere")
                print(parse.unquote(moveTo))
                moveTo = parse.unquote(moveTo.split("tree/")[1])
                print(moveTo)
                toMove = translation(checkedData)
                try:
                    moved_list = move_batch(toMove, moveTo)
                    flash_amount(moved_list, deleted=False)
                except ldap.LDAPError as e:
                    e = dict(e.args[0])
                    flash(e['info'], "error")
                return redirect(url_for('tree_base', base=base))
            # batch move (to root)
            elif moveToRoot.toRoot.data:
                checkedData = request.form.getlist("checkedItems")
                moveTo = g.ldap['search_dn']
                print(checkedData)
                toMove = translation(checkedData)
                try:
                    moved_list = move_batch(toMove, moveTo)
                    flash_amount(moved_list, deleted=False)
                except ldap.LDAPError as e:
                    e = dict(e.args[0])
                    flash(e['info'], "error")
                return redirect(url_for('tree_base'))
            # batch move (1 out)
            elif moveOneLevelUp.up_aLevel.data:
                checkedData = request.form.getlist("checkedItems")
                moveTo = parse.unquote(parent)
                toMove = translation(checkedData)
                try:
                    moved_list = move_batch(toMove, moveTo)
                    flash_amount(moved_list, deleted=False)
                    pass
                except ldap.LDAPError as e:
                    e = dict(e.args[0])
                    flash(e['info'], "error")
                return redirect(url_for('tree_base', base=base))

        name = namefrom_dn(base)
        objclass = get_objclass(base)
        return render_template("pages/tree_base_es.html", form=form, parent=parent, batch_delete=batch_delete,
                               paste=paste, moveOneLevelUp=moveOneLevelUp, moveToRoot=moveToRoot,
                               admin=admin, base=base.upper(), entries=entries, entry_fields=entry_fields, 
                               root=g.ldap['search_dn'].upper(), name=name, objclass=objclass)

    def get_entries(filter_str, filter_field, base, scope):
        """
        Get all entries that will be displayed in the tree
        """
        attr_list = [
            'name', 'showInAdvancedViewOnly', 'objectType', 'objectGUID', 'distinguishedName', 'objectClass', 
            'sAMAccountName', 'userAccountControl'
        ]
        attr_list += list(filter(lambda attr: attr not in attr_list, map(itemgetter(0), Settings.TREE_ATTRS)))
        attr_list += list(filter(lambda attr: attr not in attr_list, map(itemgetter(0), Settings.SEARCH_ATTRS)))
        assert filter_field in attr_list

        entries = ldap_get_entries(f"{filter_field}={filter_str}", base, scope, attr_list)
        users = list(sorted(
            filter(lambda entry: 'sAMAccountName' in entry and 'user' in entry['objectClass'], entries),
            key=lambda entry: entry['sAMAccountName']
        ))
        other_entries = list(sorted(
            filter(lambda entry: 'user' not in entry['objectClass'], entries),
            key=lambda entry: entry['name']
        ))

        result = []
        for entry in other_entries:
            assert entry not in users
            if 'group' in entry['objectClass']:
                entry['__target'] = url_for('group_overview',
                                            groupname=entry['sAMAccountName'])
            elif 'distinguishedName' in entry:
                entry['__target'] = url_for('tree_base', base=entry['distinguishedName'])
            entry['objectClass'] = entry['objectClass'][1]

            if Settings.TREE_WHITELIST:
                if 'distinguishedName' in entry and not entry['distinguishedName'].endswith(Settings.TREE_WHITELIST):
                    continue
            for prefix in Settings.TREE_BLACKLIST:
                if 'distinguishedName' in entry and entry['distinguishedName'].startswith(prefix):
                    break
            else:
                result.append(entry)
        for entry in users:
            if 'showInAdvancedViewOnly' in entry and entry['showInAdvancedViewOnly']:
                continue
            entry['name'] = entry['sAMAccountName']
            if 'user' in entry['objectClass']:
                if entry['userAccountControl'] & 2:  # ACCOUNTDISABLE
                    entry['active'] = "Deactivated"
                else:
                    entry['active'] = "Active"
                if 'computer' in entry['objectClass']:
                    entry['objectClass'] = 'computer'
                    entry['__target'] = url_for('computer_overview', username=entry['sAMAccountName'])
                else:
                    entry['objectClass'] = 'user'
                    if 'displayName' in entry:
                        entry['name'] = f"{entry['name']} ({entry['displayName']})"
                    entry['__target'] = url_for('user_overview', username=entry['sAMAccountName'])
            result.append(entry)
        return result

    def translation(checkedData: list):
        '''
        recieves a list of strings with format 
        ``["{name:<>, type:<>, target:<>}",...]``
        and translates them into dicts with keys: 
        ``name``, ``type``, ``username``(except if type is Organization Unit), and ``dn``;
        extracted from those string
        and returns them in a new list
        '''

        translated = []
        for x in checkedData:
            dicts = {}
            key1 = x.split("name:'")[1].split("'")[0]  # name of the object
            key2 = x.split("type:'")[1].split("'")[0]  # User, Group, Organization Unit, Container
            key3 = x.split("target:'")[1].replace("'}", "")
            key4 = parse.unquote(key3.split("/")[2])  # username
            if key2 == "User":
                user = ldap_get_user(username=key4)
                key5 = user['distinguishedName']
            elif key2 == "Group":
                group = ldap_get_group(groupname=key1)
                key5 = group['distinguishedName']
            elif key2 == "Organization Unit":
                key5 = parse.unquote(key4)
            dicts['name'] = key1
            dicts['type'] = key2
            if key2 != 'Organization Unit':
                dicts['username'] = key4
            dicts['dn'] = key5
            translated.append(dicts)
        return translated
    
    def delete_batch(translatedList: list):
        """
        Deletes the objects in the ``translatedList`` and saves the names of each element on a list to be returned
        OU objects with children will not be deleted and will have an error flash
        \n
        recieves a ``translatedList`` with the format returned by ``translation()``
        \n
        Return: a list with the names of the deleted elements
        """
        deleted_list = []
        for obj in translatedList:
            # since now there is a dn key there is no need to check what type is the current element to user the
            # ldap_get_ou(), ldap_get_user(), ldap_get_group() just to get their dn
            if obj['type'] != 'Container':
                if obj['type'] != "Organization Unit":
                    ldap_delete_entry(obj['dn'])
                    deleted_list.append(obj['name'])
                else:
                    canDelete = not ldap_obj_has_children(obj['dn'])
                    if canDelete:
                        ldap_delete_entry(obj['dn'])
                        deleted_list.append(obj['name'])
                    else:
                        flash(f"Can't delete OU: '{obj['name']}' because is not empty", "error")
            else:
                flash(f"Can't delete {obj['name']} Container", "error")
        return deleted_list

    def move_batch(translatedList: list, moveTo: str):
        """moves the elements from the list to the selected OU

        Args:
            translatedList (list): _description_
            moveTo (str): _description_

        Returns:
            a list with the names of the moved elements
        """
        print(moveTo)
        moved_list = []
        for obj in translatedList:
            moved_list.append(obj['name'])
            ldap_update_attribute(dn=obj["dn"], attribute="distinguishedName", value=obj["dn"].split(",")[0], new_parent=moveTo)
            # since now there is a dn key there is no need to check what type is the current element to user the 
            # ldap_get_ou(), ldap_get_user(), ldap_get_group() just to get their dn
        return moved_list
    
    def flash_amount(namesList: list, deleted: bool):
        """
        flashes how many elements were moved/deleted
        recieves the list returned by ``move_batch()`` or ``delete_batch()`` and an extra argument to know if elements were moved or deleted
        """
        action = "deleted" if deleted else "moved"
        if len(namesList):
            flash(f"{len(namesList)} element" + ("s " if len(namesList) > 1 else " ") + action + " successfully.", "success")
